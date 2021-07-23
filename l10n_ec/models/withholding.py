# -*- coding: utf-8 -*-
import os
import time
import logging

from datetime import datetime

from odoo import (
    api,
    fields,
    models
)
from odoo.exceptions import (
    Warning as UserError,
    ValidationError
)
from odoo.tools import float_compare, float_round
from . import utils
from itertools import groupby

from jinja2 import Environment, FileSystemLoader

from . import utils
from ..xades.sri import DocumentXML
from ..xades.xades import Xades
from .edoc import ManualAuth

def fix_date(fecha):
    d = '{0:%d/%m/%Y}'.format(fecha)
    return d

class AccountTaxDetail(models.Model):
    _name = 'account.retention.line'

    amount = fields.Float('Monto')
    base = fields.Float('Base')
    group_id = fields.Many2one('account.tax.group')
    tax_id = fields.Many2one('account.tax')
    tax_repartition_line_id = fields.Many2one('account.tax.repartition.line')
    retention_id = fields.Many2one('account.retention')
    num_document = fields.Char('Numero documento')
    fiscal_year = fields.Char('Periodo Fiscal')
    code = fields.Char('Codigo', related="tax_id.description", readonly=True)
    name = fields.Char('Nombre', related="tax_id.name", readonly=True)
    sequence = fields.Integer('Secuencia')
    account_id = fields.Many2one('account.account', string="Cuenta")
    

class AccountWithdrawing(models.Model):
    """ Implementacion de documento de retencion """

    
    def _get_in_type(self):
        context = self._context
        return context.get('in_type', 'ret_out_invoice')

    
    def _default_type(self):
        context = self._context
        return context.get('type', 'out_invoice')

    @api.model
    def _default_currency(self):
        company = self.env['res.company']._company_default_get('account.move')  # noqa
        return company.currency_id

    @api.model
    def _default_authorisation(self):
        if self.env.context.get('in_type') == 'ret_in_invoice':
            company = self.env['res.company']._company_default_get('account.move')  # noqa
            auth_ret = company.partner_id.get_authorisation('ret_in_invoice')
            return auth_ret

    STATES_VALUE = {'draft': [('readonly', False)]}

    _name = 'account.retention'
    _inherit = ['account.edocument', 'mail.thread', 'mail.activity.mixin']
    _description = 'Withdrawing Documents'
    _order = 'date DESC'
    _logger = logging.getLogger(_name)

    name = fields.Char(
        'Número',
        size=64,
        readonly=True,
        states=STATES_VALUE,
        copy=False
        )
    internal_number = fields.Char(
        'Número Interno',
        size=64,
        readonly=True,
        copy=False
        )
    manual = fields.Boolean(
        'Numeración Manual',
        readonly=True,
        states=STATES_VALUE,
        default=True
        )
    auth_id = fields.Many2one(
        'account.authorisation',
        'Autorizacion',
        readonly=True,
        states=STATES_VALUE,
        domain=[('in_type', '=', 'interno')],
        default=_default_authorisation
        )
    auth_number = fields.Char('Numero de autorizacion',
        readonly=True,
        states=STATES_VALUE,
        )
    type = fields.Selection(
        related='invoice_id.type',
        string='Tipo Comprobante',
        readonly=True,
        store=True,
        default=_default_type
        )
    in_type = fields.Selection(
        [
            ('ret_in_invoice', u'Retención a Proveedor'),
            ('ret_out_invoice', u'Retención de Cliente'),
            ('ret_in_refund', u'Retención Nota de Credito Proveedor'),
            ('ret_out_refund', u'Retención Nota de Credito Cliente'),
            ('ret_liq_purchase', u'Retención de Liquidación en Compras'),
            ('ret_in_debit', u'Retención de Nota de Debito Proveedor'),
            ('ret_out_debit', u'Retención Nota de Debito Cliente'),
        ],
        string='Tipo',
        readonly=True,
        default=_get_in_type
        )
    date = fields.Date(
        'Fecha Emision',
        readonly=True,
        states={'draft': [('readonly', False)]}, required=True
    )
    tax_ids = fields.One2many(
        'account.retention.line',
        'retention_id',
        'Detalle de Impuestos',
        readonly=True,
        states=STATES_VALUE,
        copy=False
        )

    invoice_id = fields.Many2one(
        'account.move',
        string='Documento',
        required=False,
        readonly=True,
        states=STATES_VALUE,
        domain=[('state', '=', 'open')],
        copy=False
        )
    partner_id = fields.Many2one(
        'res.partner',
        string='Empresa',
        required=True,
        readonly=True,
        states=STATES_VALUE
        )
    
    move_ret_id = fields.Many2one(
        'account.move',
        string='Asiento Retención',
        readonly=True,
        copy=False
        )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('done', 'Validado'),
            ('cancel', 'Anulado')
        ],
        readonly=True,
        string='Estado',
        default='draft'
        )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=_default_currency
    )
    amount_total = fields.Monetary(
        compute='_compute_total',
        string='Total',
        store=True,
        readonly=True
        )
    to_cancel = fields.Boolean(
        string='Para anulación',
        readonly=True,
        states=STATES_VALUE
        )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.move')  # noqa
        )
    sri_sent = fields.Boolean('Enviado', default=False)
    sri_errors = fields.One2many('sri.error','retencion_id', string='Errores SRI')

    _sql_constraints = [
        (
            'unique_number_type',
            'unique(name,type,partner_id)',
            u'El número de retención es único.'
        )
    ]

    @api.constrains('auth_number')
    def check_reference(self):
        """
        Metodo que verifica la longitud de la autorizacion
        10: documento fisico
        35: factura electronica modo online
        49: factura electronica modo offline
        """
        if self.type not in ['out_invoice', ]:
            return
        if self.auth_number and len(self.auth_number) not in [10, 35, 49]:
            raise UserError(
                u'Debe ingresar 10, 35 o 49 dígitos según el documento.'
            )


    #@api.onchange('date')
    #@api.constrains('date')
    #def _check_date(self):
        
     #   if self.date and self.invoice_id:
     #       inv_date = datetime.strptime(self.invoice_id.invoice_date, '%Y-%m-%d')  # noqa
     #       ret_date = datetime.strptime(self.date, '%Y-%m-%d')  # noqa
     #       days = ret_date - inv_date
            #if days.days not in range(1, 6):
            #    raise ValidationError(utils.CODE_701)  # noqa

    # 
    # def name_get(self):
    #     result = []
    #     for inv in self:
    #         result.append((inv.id,'%s%s%s' % (inv.auth_id.serie_entidad, inv.auth_id.serie_emision, inv.name)))
    #     return result

    @api.depends('tax_ids.amount')
    def _compute_total(self):
        """
        TODO
        """
        _get_rounded_value = lambda x: isinstance(x, float) and float_round(
            x, precision_rounding=self.currency_id.rounding,
        ) or x
        for s in self:
            s.amount_total = sum(_get_rounded_value(tax.amount) for tax in s.tax_ids)

    @api.onchange('name')
    @api.constrains('name')
    def _onchange_name(self):
        length = {
            'in_invoice': 15,
            'liq_purchase': 15,
            'out_invoice': 15,
            'out_debit': 15,
            'in_debit': 15
        }
        if not self.name or not self.type:
            return
        if not len(self.name) == length[self.type] or not self.name.isdigit():
            raise UserError(u'Nro incorrecto. Debe ser de 15 dígitos. %s' %(self.name))
        if self.in_type == 'ret_in_invoice':
            if not self.auth_id.is_valid_number(int(self.name[6:])):
                raise UserError('Nro no pertenece a la secuencia.')

    
    def unlink(self):
        for obj in self:
            if obj.state in ['done']:
                raise UserError('No se permite borrar retenciones validadas.')
        res = super(AccountWithdrawing, self).unlink()
        return res

    @api.onchange('to_cancel')
    def onchange_tocancel(self):
        if self.to_cancel:
            company = self.env['res.company']._company_default_get('account.move')  # noqa
            self.partner_id = company.partner_id.id

    @api.onchange('invoice_id')
    def onchange_invoice(self):
        if not self.invoice_id:
            return
        self.type = self.invoice_id.type

    
    def action_number(self, number):
        for wd in self:
            if wd.to_cancel:
                raise UserError('El documento fue marcado para anular.')

            sequence = wd.auth_id.sequence_id
            if self.type != 'out_invoice' and not number:
                number = sequence.next_by_id()
                wd.write({
                    'name': '%s%s%09s'%(self.auth_id.serie_entidad, self.auth_id.serie_emision, number)
                })
        return True
    
    def get_base_line_report(self,linea):
            if linea.group_id.code in ['ret_vat_b', 'ret_vat_srv']:
                return linea.base*12.0/100.0
            return linea.base
    
    def action_validate(self, number=None):
        """
        @number: Número para usar en el documento
        """
        self.action_number(number)
        return self.write({'state': 'done'})

    
    def button_validate(self):
        """
        Botón de validación de Retención que se usa cuando
        se creó una retención manual, esta se relacionará
        con la factura seleccionada.
        """
        for ret in self:
            if not ret.tax_ids:
                raise UserError('No ha aplicado impuestos.')
            self.action_validate(self.name)
            if ret.manual:
                ret.invoice_id.write({'retention_id': ret.id})
            self.create_move()
        return True

    
    def create_move(self):
        """
        Generacion de asiento contable para aplicar como
        pago a factura relacionada
        """
        for ret in self:
            inv = ret.invoice_id
            move_data = {
                'journal_id': inv.journal_id.id,
                'ref': ret.name,
                'date': ret.date
            }
            total_counter = 0
            lines = []
            
            for line in ret.tax_ids:
                lines.append((0, 0, {
                    'partner_id': ret.partner_id.id,
                    'account_id': line.tax_repartition_line_id.account_id.id,
                    'name': ret.name,
                    'debit': abs(line.amount),
                    'credit': 0.00
                }))

                total_counter += abs(line.amount)
            rec_account = inv.partner_id.property_account_receivable_id.id
            pay_account = inv.partner_id.property_account_payable_id.id
            lines.append((0, 0, {
                'partner_id': ret.partner_id.id,
                'account_id': ret.in_type == 'ret_in_invoice' and pay_account or rec_account,
                'name': ret.name,
                'debit': 0.00,
                'credit': total_counter
            }))
            move_data.update({'line_ids': lines})
            move = self.env['account.move'].create(move_data)
            acctype = self.type == 'in_invoice' and 'payable' or 'receivable'
            inv_lines = inv.line_ids
            acc2rec = inv_lines.filtered(lambda l: l.account_id.internal_type == acctype)  # noqa
            acc2rec += move.line_ids.filtered(lambda l: l.account_id.internal_type == acctype)  # noqa
            acc2rec.auto_reconcile_lines()
            ret.write({'move_ret_id': move.id})
            move.post()
        return True

    
    def action_cancel(self):
        """
        Método para cambiar de estado a cancelado el documento
        """
        for ret in self:
            if ret.move_ret_id:
                ret.move_ret_id.reverse_moves()
                continue
            
            ret.invoice_id.write({
                'retention_id': None
            })
            self.env.cr.commit()
            ret.invoice_id.button_draft()

            data = {'state': 'cancel'}
            if ret.to_cancel:
                # FIXME
                if len(ret.name) == 9 and ret.auth_id.is_valid_number(int(ret.name)):  # noqa
                    number = ret.auth_id.serie_entidad + ret.auth_id.serie_emision + ret.name  # noqa
                    data.update({'name': number})
                else:
                    raise UserError(utils.CODE702)
            #self.tax_ids.write({'invoice_id': False})
            self.write({'state': 'cancel'})
        return True

    
    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    
    def action_print(self):
        # Método para imprimir comprobante contable
        return self.env['report'].get_action(
            self.move_id,
            'l10n_ec.account_withholding'
        )

    def print_retention(self):
        """
        Método para imprimir reporte de retencion
        """
        return self.env.ref('l10n_ec.account_retenciones').report_action(self)

    
    def retention_print(self):
        """
        Método para imprimir reporte de retencion
        """
        return self.env.ref('l10n_ec.account_retenciones').report_action(self)

    def get_secuencial(self):
        return getattr(self, 'name')[6:15]

    def _info_withdrawing(self, withdrawing):
        """
        """

        
        # generar infoTributaria
        company = withdrawing.company_id
        partner = withdrawing.invoice_id.partner_id
        infoCompRetencion = {
            'fechaEmision': fix_date(withdrawing.date),  # noqa
            'dirEstablecimiento': company.street,
            'obligadoContabilidad': 'SI',
            'tipoIdentificacionSujetoRetenido': utils.tipoIdentificacion[partner.type_identifier],  # noqa
            'razonSocialSujetoRetenido': partner.name.replace('&', '&amp;'),
            'identificacionSujetoRetenido': partner.identifier,
            'periodoFiscal': '{0:%m/%Y}'.format(withdrawing.date),
            # 'Resolucion':company.resolution_number,
            # 'ret_agent': company.withholding_agent
            }
        if company.company_registry:
            infoCompRetencion.update({'contribuyenteEspecial': company.company_registry})  # noqa
        return infoCompRetencion

    def get_base_line_report(self,linea):
            if linea.group_id.code in ['ret_vat_b', 'ret_vat_srv']:
                return linea.base*12.0/100.0
            return linea.base

    def _impuestos(self, retention):
        """
        """
        def get_original_tax_percent(linea):
            if linea.group_id.code in ['ret_vat_b', 'ret_vat_srv']:
                return linea.tax_id.amount
            return linea.tax_id.amount

        def get_base_line(linea):
            if linea.group_id.code in ['ret_vat_b', 'ret_vat_srv']:
                return linea.base*12.0/100.0
            return linea.base

        def get_codigo_retencion(linea):
            if linea.group_id.code in ['ret_vat_b', 'ret_vat_srv']:
                return utils.tabla21[str(int(abs(get_original_tax_percent(linea))))]
            #else:
            code = linea.code
            return code

        impuestos = []
        for line in retention.tax_ids:
            impuesto = {
                'codigo': utils.tabla20[line.group_id.code],
                'codigoRetencion': get_codigo_retencion(line),
                'baseImponible': '%.2f' % (get_base_line(line)),
                'porcentajeRetener': str(abs(float(get_original_tax_percent(line)))),
                'valorRetenido': '%.2f' % (abs(line.amount)),
                'codDocSustento': utils.tipoDocumento[retention.invoice_id.auth_inv_id.type_id.code],
                'numDocSustento': retention.invoice_id.sudo().invoice_number,
                'fechaEmisionDocSustento': fix_date(retention.invoice_id.sudo().invoice_date)  # noqa
            }
            impuestos.append(impuesto)
        return {'impuestos': impuestos}

    def render_document(self, document, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ewithdrawing_tmpl = env.get_template('ewithdrawing.xml')
        data = {}
        data.update(self._info_tributaria(document, access_key, emission_code))
        data.update(self._info_withdrawing(document))
        data.update(self._impuestos(document))
        edocument = ewithdrawing_tmpl.render(data)
        self._logger.debug(edocument)
        return edocument, data

    def render_authorized_document(self, autorizacion, doc, xml):
        print(autorizacion)
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        edocument_tmpl = env.get_template('authorized_withdrawing.xml')
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': doc['claveAcceso'],
            'ambiente': self.company_id.env_service,
            'fechaAutorizacion': "{0:%d/%m/%Y %H:%M:%S}".format(datetime.now()), 
            'comprobante': xml
        }
        auth_withdrawing = edocument_tmpl.render(auth_xml)
        return auth_withdrawing

    def button_elec(self):
        """
        """
        for obj in self:
            #self.check_date(obj.date)
        
            self.check_before_sent()
            if not self.clave_acceso:
                access_key, emission_code = self._get_codes('account.retention')
            else:
                access_key, emission_code = (self.clave_acceso, self.company_id.emission_code)
            ewithdrawing, data = self.render_document(obj, access_key, emission_code)
            self._logger.debug(ewithdrawing)
            inv_xml = DocumentXML(ewithdrawing, 'withdrawing')
            inv_xml.validate_xml()
            xades = Xades()
            file_pk12 = obj.company_id.electronic_signature
            password = obj.company_id.password_electronic_signature
            signed_document = xades.sign(ewithdrawing, file_pk12, password)
            self.SriServiceObj.set_active_env(self.company_id.env_service)
            #try:
            ok, errores = inv_xml.send_receipt(signed_document)
            #except Exception as e:
            #    raise UserError(e)
            if not ok:
            
                if "REGISTRAD" in errores:
                    obj.sri_sent = True
                else:
                    err_obj=obj.env['sri.error']
                    err_obj.create({
                        'message': errores,
                        'state': 'error',
                        'retencion_id': obj.id
                    })
                    obj.env.cr.commit()
                    return {
                        'name': 'Error SRI',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'view_id': obj.env.ref('l10n_ec.sri_error_view')[0].id,
                        'res_model': 'account.retention',
                        'src_model': 'account.retention',
                        'context': "{}",
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'readonly': True,
                        'res_id': obj.id
                    }
            obj.sri_sent=True
            auth = None
            try:
                auth, m = inv_xml.request_authorization(access_key)
            except Exception as e:
                raise UserError(e)
            if not auth:
                auth = ManualAuth()
                auth.numeroAutorizacion = obj.clave_acceso
                auth.estado = "EN PROCESO"
                auth.ambiente = obj.ambiente
                auth.autorizado_sri = False
                auth.fechaAutorizacion = ''
            auth_document = self.render_authorized_document(auth, data, ewithdrawing)
            auth.numeroAutorizacion = data['claveAcceso']
            self.update_document(auth, [access_key, emission_code])
            attach = self.add_attachment(auth_document, auth)
            self.send_document(
                attachments=attach,
                tmpl='l10n_ec.email_template_eretention'
            )
            return True
