# -*- coding: utf-8 -*-

import base64
import io
import os
import logging
from itertools import groupby
from operator import itemgetter

from lxml import etree
from lxml.etree import DocumentInvalid
from jinja2 import Environment, FileSystemLoader

from openerp import fields, models, api

from .utils import convertir_fecha, get_date_value
from odoo.exceptions import ValidationError

tpIdProv = {
    'ruc': '01',
    'cedula': '02',
    'pasaporte': '03',
    'nit': '03'
}

tpIdCliente = {
    'ruc': '04',
    'cedula': '05',
    'pasaporte': '06',
    'final': '07',
    'nit': '08'
    }


class AccountAts(dict):
    """
    representacion del ATS
    >>> ats.campo = 'valor'
    >>> ats['campo']
    'valor'
    """

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, item, value):
        if item in self.__dict__:
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)


class WizardAts(models.TransientModel):

    _name = 'wizard.ats'
    _description = 'Anexo Transaccional Simplificado'
    __logger = logging.getLogger(_name)

    
    def _get_period(self):
        return None #self.env['account.period'].search([])

    
    def _get_company(self):
        return self.env.company.id

    def act_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def process_lines(self, lines):
        """
        @temp: {'332': {baseImpAir: 0,}}
        @data_air: [{baseImpAir: 0, ...}]
        """
        data_air = []
        temp = {}
        for line in lines:
            for tax in line.tax_ids:
                if tax.tax_group_id.code in ['ret_ir', 'no_ret_ir']:
                    if not temp.get(tax.description):
                        temp[tax.description] = {
                            'baseImpAir': 0,
                            'valRetAir': 0
                        }
                    temp[tax.description]['baseImpAir'] += line.price_subtotal
                    temp[tax.description]['codRetAir'] = tax.description  # noqa
                    temp[tax.description]['porcentajeAir'] = abs(float(tax.amount))  # noqa
                    temp[tax.description]['valRetAir'] += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))
        for k, v in temp.items():
            data_air.append(v)
        return data_air

    @api.model
    def _get_ventas(self, start, end):
        sql_ventas = "SELECT inv.type, sum(amount_untaxed) AS base \
                      FROM account_move AS inv\
                      LEFT JOIN account_authorisation AS auth ON inv.auth_inv_id=auth.id \
                      WHERE inv.type IN ('out_invoice', 'out_refund') \
                      AND inv.state IN ('posted') \
                      AND inv.invoice_date >= '%s' \
                      AND inv.invoice_date <= '%s' \
                      AND inv.company_id = %d \
                      " % (start, end, self.company_id.id) 

                      #AND auth.is_electronic != true \
        sql_ventas += " GROUP BY inv.type"
        self.env.cr.execute(sql_ventas)
        res = self.env.cr.fetchall()
        resultado = sum(map(lambda x: x[0] == 'out_refund' and x[1] * -1 or x[1], res))  # noqa
        return resultado

    def _get_ret_iva(self, invoice):
        """
        Return (valRetBien10, valRetServ20,
        valorRetBienes,
        valorRetServicios, valorRetServ100)
        """
        retBien10 = 0
        retServ20 = 0
        retBien = 0
        retServ = 0
        retServ100 = 0
        for line in invoice.invoice_line_ids:
            for tax in line.tax_ids:
                if tax.tax_group_id.code == 'ret_vat_b':
                    if abs(tax.amount) == 10:
                        retBien10 += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))*0.12
                    else:
                        retBien += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))*0.12
                if tax.tax_group_id.code == 'ret_vat_srv':
                    if abs(tax.amount) == 100:
                        retServ100 += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))*0.12
                    elif abs(tax.amount) == 20:
                        retServ20 += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))*0.12
                    else:
                        retServ += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))*0.12
        return retBien10, retServ20, retBien, retServ, retServ100

    def _get_iva_types(self, invoice):
        iva12 = 0
        iva0 = 0
        novat = 0
        for line in invoice.invoice_line_ids:
            for tax in line.tax_ids:
                if tax.tax_group_id.code == 'vat':
                    iva12 += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))
                if tax.tax_group_id.code == 'vat0':
                    iva0 += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))
                if tax.tax_group_id.code == 'novat':
                    novat += abs(tax._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))
        
        return iva12, iva0, novat

    def _get_iva_bases(self, invoice):
        iva12 = 0
        iva0 = 0
        novat = 0
        for line in invoice.invoice_line_ids:
            for tax in line.tax_ids:
                if tax.tax_group_id.code == 'vat':
                    iva12 += abs(line.price_subtotal)
                if tax.tax_group_id.code == 'vat0':
                    iva0 += abs(line.price_subtotal)
                if tax.tax_group_id.code == 'novat':
                    novat += abs(line.price_subtotal)
        
        return iva12, iva0, novat
                


    def get_withholding(self, wh):
        if wh.auth_id.is_electronic:
            authRetencion = wh.numero_autorizacion
        else:
            authRetencion = wh.auth_id.name
        return {
            'estabRetencion1': wh.auth_id.serie_entidad,
            'ptoEmiRetencion1': wh.auth_id.serie_emision,
            'secRetencion1': wh.name[6:15],
            'autRetencion1': authRetencion,
            'fechaEmiRet1': convertir_fecha(wh.date)
        }

    def get_refund(self, invoice):
        refund = self.env['account.move'].search([
            ('invoice_number', '=', invoice.reversed_entry_id.invoice_number),('state','not in',('draft','cancel'))
        ])
        if refund:
            auth = refund.auth_inv_id
            if auth.is_electronic:
                aut = refund.numero_autorizacion
            else:
                aut = auth.name
            return {
                'docModificado': '01',
                'estabModificado': refund.invoice_number[0:3],
                'ptoEmiModificado': refund.invoice_number[3:6],
                'secModificado': refund.invoice_number[6:],
                'autModificado': aut,
            }
        else:
            return {}
            # auth = refund.auth_inv_id
            # return {
            #     'docModificado': auth.type_id.code,
            #     'estabModificado': auth.serie_entidad,
            #     'ptoEmiModificado': auth.serie_emision,
            #     'secModificado': refund.invoice_number[6:15],
            #     'autModificado': refund.reference
            # }

    def get_reembolsos(self, invoice):
        if not invoice.auth_inv_id.type_id.code == '41':
            return False
        res = []
        for r in invoice.refund_ids:
            res.append({
                'tipoComprobanteReemb': r.doc_id.code,
                'tpIdProvReemb': tpIdProv[r.partner_id.type_identifier],
                'idProvReemb': r.partner_id.identifier,
                'establecimientoReemb': r.auth_id.serie_entidad,
                'puntoEmisionReemb': r.auth_id.serie_emision,
                'secuencialReemb': r.secuencial,
                'fechaEmisionReemb': convertir_fecha(r.date),
                'autorizacionReemb': r.auth_id.name,
                'baseImponibleReemb': '0.00',
                'baseImpGravReemb': '0.00',
                'baseNoGravReemb': '%.2f' % r.amount,
                'baseImpExeReemb': '0.00',
                'montoIceRemb': '0.00',
                'montoIvaRemb': '%.2f' % r.tax
            })
        return res

    def si_no(self, condition):
        if condition:
             return 'SI'
        return 'NO'

    def read_compras(self, start, end):
        """
        Procesa:
          * facturas de proveedor
          * liquidaciones de compra
        """
        inv_obj = self.env['account.move']
        dmn_purchase = [
            ('state', 'in', ['posted']),
            ('invoice_date', '>=', '{0:%Y-%m-%d}'.format(start)),
            ('invoice_date', '<=',  '{0:%Y-%m-%d}'.format(end)),
            ('type', 'in', ['in_invoice', 'liq_purchase', 'in_refund', 'in_debit'])  # noqa
        ]
        compras = []
        for inv in inv_obj.search(dmn_purchase):
            if inv.partner_id.type_identifier not in ['pasaporte','final']:
                detallecompras = {}
                auth = inv.auth_inv_id
                valRetBien10, valRetServ20, valorRetBienes, valorRetServicios, valRetServ100 = self._get_ret_iva(inv)  # noqa
                iva12, iva0, novat = self._get_iva_types(inv)
                baseiva12, baseiva0, basenovat= self._get_iva_bases(inv)
                t_reeb = 0.0
                if not inv.auth_inv_id.type_id.code == '41':
                    t_reeb = 0.00
                else:
                    if inv.type == 'liq_purchase':
                        t_reeb = 0.0
                    else:
                        t_reeb = inv.amount_untaxed
                detallecompras.update({
                    'codSustento': inv.sustento_id.code,
                    'tpIdProv': tpIdProv[inv.partner_id.type_identifier],
                    'idProv': inv.partner_id.identifier,
                    'tipoComprobante': inv.type == 'liq_purchase' and '03' or auth.type_id.code,  # noqa
                    'parteRel': 'NO',
                    'fechaRegistro': convertir_fecha(inv.invoice_date),
                    'establecimiento': inv.invoice_number[:3],
                    'puntoEmision': inv.invoice_number[3:6],
                    'secuencial': inv.invoice_number[6:15],
                    'fechaEmision': convertir_fecha(inv.invoice_date),
                    'autorizacion': inv.auth_number,
                    'baseNoGraIva': '%.2f' % basenovat,
                    'baseImponible': '%.2f' % baseiva0,
                    'baseImpGrav': '%.2f' % baseiva12,
                    'baseImpExe': '0.00',
                    'total': inv.amount_total+(valRetBien10+valRetServ20+valorRetBienes+valorRetServicios+valRetServ100),
                    'montoIce': '0.00',
                    'montoIva': '%.2f' % iva12,
                    'valRetBien10': '%.2f' % valRetBien10,
                    'valRetServ20': '%.2f' % valRetServ20,
                    'valorRetBienes': '%.2f' % valorRetBienes,
                    'valRetServ50': '0.00',
                    'valorRetServicios': '%.2f' % valorRetServicios,
                    'valRetServ100': '%.2f' % valRetServ100,
                    'totbasesImpReemb': '%.2f' % t_reeb,
                    'pagoExterior': {
                        'pagoLocExt': inv.partner_id.ats_resident,
                        'tipoRegi': inv.partner_id.ats_regimen_fiscal,
                        'pais': inv.partner_id.ats_country,
                        'pais_efec_gen': inv.partner_id.ats_country_efec_gen,
                        'pais_efec_par_fic': inv.partner_id.ats_country_efec_parfic,
                        'aplicConvDobTrib': self.si_no(inv.partner_id.ats_doble_trib),
                        'denopago': inv.partner_id.denopago,
                        'pagExtSujRetNorLeg': self._pagExtSujRetNorLeg(inv),
                        'pagoRegFis': self.si_no(inv.partner_id.pago_reg_fis)
                    },
                    'formaPago': inv.epayment_id.code,
                    'detalleAir': self.process_lines(inv.invoice_line_ids)
                })
                if inv.retention_id:
                    detallecompras.update({'retencion': True})
                    detallecompras.update(self.get_withholding(inv.retention_id))  # noqa
                if inv.type in ['out_refund', 'in_refund']:
                    refund = self.get_refund(inv)
                    if refund:
                        detallecompras.update({'es_nc': True})
                        detallecompras.update(refund)
                detallecompras.update({
                    'reembolsos': self.get_reembolsos(inv)
                })
                compras.append(detallecompras)
        logging.error(compras)
        return compras

    def _pagExtSujRetNorLeg(self, inv):
        if inv.partner_id.ats_doble_trib:
            return self.si_no(inv.partner_id.pag_ext_suj_ret_nor_leg)
        else:
            return 'NA'

    
    def read_ventas(self, start, end):
        dmn = [
            ('state', 'in', ['posted']),
            ('invoice_date','>=', '{0:%Y-%m-%d}'.format(start)),
            ('invoice_date', '<=', '{0:%Y-%m-%d}'.format(end)),
            ('type', '=', 'out_invoice'),
            ('auth_inv_id.is_electronic', '!=', True)
        ]
        ventas = []
        for inv in self.env['account.move'].search(dmn):
            valRetBien10, valRetServ20, valorRetBienes, valorRetServicios, valRetServ100 = self._get_ret_iva(inv)  # noqa
            iva12, iva0, novat = self._get_iva_types(inv)
            baseiva12, baseiva0, basenovat = self._get_iva_bases(inv)
            detalleventas = {
                'tpIdCliente': tpIdCliente[inv.partner_id.type_identifier],
                'idCliente': inv.partner_id.identifier,
                'parteRelVtas': 'NO',
                'partner': inv.partner_id,
                'auth': inv.auth_inv_id,
                'tipoComprobante': inv.auth_inv_id.type_id.code,
                'tipoEmision': inv.auth_inv_id.is_electronic and 'E' or 'F',
                'numeroComprobantes': 1,
                'baseNoGraIva': basenovat,
                'baseImponible': baseiva0,
                'baseImpGrav': baseiva12,
                'montoIva': iva12,
                'montoIce': '0.00',
                'valorRetIva': (abs(valorRetBienes) + abs(valorRetServicios)),  # noqa
                'valorRetRenta': abs(valRetBien10)+abs(valRetServ20)+abs(valRetServ100),
                'formasDePago': {
                    'formaPago': inv.epayment_id.code
                }
            }
            ventas.append(detalleventas)
        ventas = sorted(ventas, key=itemgetter('idCliente'))
        ventas_end = []
        for ruc, grupo in groupby(ventas, key=itemgetter('idCliente')):
            baseimp = 0
            nograviva = 0
            montoiva = 0
            retiva = 0
            impgrav = 0
            retrenta = 0
            numComp = 0
            partner_temp = False
            auth_temp = False
            for i in grupo:
                nograviva += i['baseNoGraIva']
                baseimp += i['baseImponible']
                impgrav += i['baseImpGrav']
                montoiva += i['montoIva']
                retiva += i['valorRetIva']
                retrenta += i['valorRetRenta']
                numComp += 1
                partner_temp = i['partner']
                auth_temp = i['auth']
            detalle = {
                'tpIdCliente': tpIdCliente[partner_temp.type_identifier],
                'idCliente': ruc,
                'parteRelVtas': 'NO',
                'tipoComprobante': auth_temp.type_id.code,
                'tipoEmision': auth_temp.is_electronic and 'E' or 'F',
                'numeroComprobantes': numComp,
                'baseNoGraIva': '%.2f' % nograviva,
                'baseImponible': '%.2f' % baseimp,
                'baseImpGrav': '%.2f' % impgrav,
                'montoIva': '%.2f' % montoiva,
                'montoIce': '0.00',
                'valorRetIva': '%.2f' % retiva,
                'valorRetRenta': '%.2f' % retrenta,
                'formasDePago': {
                    'formaPago': '20'
                }
            }
            ventas_end.append(detalle)
        return ventas_end

    
    def read_anulados(self, start, end):
        dmn = [
            ('state', '=', 'cancel'),
            ('invoice_date', '>=', '%s'%start),
            ('invoice_date', '<=', '%s'%end),
            ('type', 'in', ['out_invoice', 'liq_purchase']),
            ('invoice_number', '!=', '*')
        ]
        anulados = []
        anulados_nums=[]
        for inv in self.env['account.move'].search(dmn):
            if inv.invoice_number[6:].lstrip("0") not in anulados_nums:
                auth = inv.auth_inv_id
                if auth.is_electronic:
                    aut=inv.numero_autorizacion
                else:
                    aut=auth.name
                detalleanulados = {
                    'tipoComprobante': auth.type_id.code,
                    'establecimiento': auth.serie_entidad,
                    'ptoEmision': auth.serie_emision,
                    'secuencialInicio': inv.invoice_number[6:].lstrip("0"),
                    'secuencialFin': inv.invoice_number[6:].lstrip("0"),
                    'autorizacion': aut or '9999'
                }
                anulados.append(detalleanulados)
                anulados_nums.append(inv.invoice_number[6:].lstrip("0"))

        dmn_ret = [
            ('state', '=', 'cancel'),
            ('date', '>=', '%s'%start),
            ('date', '<=', '%s'%end),
            ('in_type', '=', 'ret_in_invoice')
        ]
        anulados_nums = []
        for ret in self.env['account.retention'].search(dmn_ret):
            if ret.name[6:].lstrip("0") not in anulados_nums:
                auth = ret.auth_id
                if auth.is_electronic:
                    aut=ret.numero_autorizacion
                else:
                    aut=auth.name
                detalleanulados = {
                    'tipoComprobante': auth.type_id.code,
                    'establecimiento': auth.serie_entidad,
                    'ptoEmision': auth.serie_emision,
                    'secuencialInicio': ret.name[6:].lstrip("0"),
                    'secuencialFin': ret.name[6:].lstrip("0"),
                    'autorizacion': aut or '9999'
                }
                anulados.append(detalleanulados)
                anulados_nums.append(ret.name[6:].lstrip("0"))
        return anulados

    
    def render_xml(self, ats):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ats_tmpl = env.get_template('ats.xml')
        return ats_tmpl.render(ats)

    
    def validate_document(self, ats, error_log=False):
        file_path = os.path.join(os.path.dirname(__file__), 'XSD/ats.xsd')
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        root = etree.fromstring(ats.encode())
        ok = True
        if not self.no_validate:
            try:
                xmlschema.assertValid(root)
            except DocumentInvalid:
                ok = False
        return ok, xmlschema

    
    def act_export_ats(self):
        ats = AccountAts()
        period = self.period_id
        ruc = self.company_id.partner_id.identifier
        ats.TipoIDInformante = 'R'
        ats.IdInformante = ruc
        ats.razonSocial = self.company_id.name.upper()
        ats.Anio = get_date_value(self.period_start, '%Y')
        ats.Mes = get_date_value(self.period_start, '%m')
        ats.numEstabRuc = self.num_estab_ruc.zfill(3)
        ats.AtstotalVentas = '%.2f' % self._get_ventas(self.period_start, self.period_end)
        #ats.totalVentas = '%.2f' % self._get_ventas(self.period_start, self.period_end)
        ats.codigoOperativo = 'IVA'
        ats.compras = self.read_compras(self.period_start, self.period_end)
        ats.codEstab = self.num_estab_ruc
        ats.ventas = self.read_ventas(self.period_start, self.period_end)
        ats.ventasEstab = '%.2f' % sum([(float(v['baseNoGraIva'])+float(v['baseImponible'])+float(v['baseImpGrav'])) for v in ats.ventas]) #'%.2f' % self._get_ventas(self.period_start, self.period_end)
        ats.totalVentas = ats.ventasEstab
        ats.ivaComp = '0.00'
        ats.anulados = self.read_anulados(self.period_start, self.period_end)
        ats_rendered = self.render_xml(ats)
        ok, schema = self.validate_document(ats_rendered)
        buf = io.StringIO()
        buf.write(ats_rendered)
        out = base64.encodestring(buf.getvalue().encode('utf-8')).decode()
        logging.error(out)
        buf.close()
        buf_erro = io.StringIO()
        for err in schema.error_log:
            buf_erro.write(err.message+'\n')
        #buf_erro.write(schema.error_log)
        out_erro = base64.encodestring(buf_erro.getvalue().encode())
        buf_erro.close()
        name = "%s%s%s.XML" % (
            "AT",
            ats.Mes,
            ats.Anio
        )
        data2save = {
            'state': ok and 'export' or 'export_error',
            'data': out,
            'fcname': name
        }
        if not ok:
            data2save.update({
                'error_data': out_erro,
                'fcname_errores': 'ERRORES.txt'
            })
        self.write(data2save)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.ats',
            'view_mode': ' form',
            'view_type': ' form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    fcname = fields.Char('Nombre de Archivo', size=50, readonly=True)
    fcname_errores = fields.Char('Archivo Errores', size=50, readonly=True)
    period_id = fields.Many2one(
        'account.period',
        'Periodo',
        #default=_get_period
    )
    period_start = fields.Date('Inicio de periodo')
    period_end = fields.Date('Fin de periodo')
    company_id = fields.Many2one(
        'res.company',
        'Compania',
        default=_get_company
    )
    num_estab_ruc = fields.Char(
        'Num. de Establecimientos',
        size=3,
        required=True,
        default='001'
    )
    pay_limit = fields.Float('Limite de Pago', default=1000)
    data = fields.Binary('Archivo XML')
    error_data = fields.Binary('Archivo de Errores')
    no_validate = fields.Boolean('No Validar', default=True)
    state = fields.Selection(
        (
            ('choose', 'Elegir'),
            ('export', 'Generado'),
            ('export_error', 'Error')
        ),
        string='Estado',
        default='choose'
    )
