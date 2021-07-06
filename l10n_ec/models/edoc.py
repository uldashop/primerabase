# -*- coding: utf-8 -*-

import base64
import io
from datetime import datetime,date

from odoo import api, fields, models
from odoo.exceptions import Warning as UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


from . import utils
from ..xades.sri import SriService


class ManualAuth(dict):

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


class AccountEpayment(models.Model):
    _name = 'account.epayment'

    code = fields.Char('Código')
    name = fields.Char('Forma de Pago')


class Edocument(models.AbstractModel):

    _name = 'account.edocument'
    _FIELDS = {
        'account.move': 'invoice_number',
        'account.retention': 'name',
        'account.guia.remision': 'name'
    }
    SriServiceObj = SriService()

    clave_acceso = fields.Char(
        'Clave de Acceso',
        size=49,
        readonly=True,
        copy=False
    )
    numero_autorizacion = fields.Char(
        'Número de Autorización',
        size=49,
        readonly=True,
        copy=False
    )
    estado_autorizacion = fields.Char(
        'Estado de Autorización',
        size=64,
        readonly=True,copy=False
    )
    fecha_autorizacion = fields.Datetime(
        'Fecha Autorización',
        readonly=True,copy=False
    )
    ambiente = fields.Char(
        'Ambiente',
        size=64,
        readonly=True,copy=False
    )
    autorizado_sri = fields.Boolean('¿Autorizado SRI?', readonly=True, copy=False)
    security_code = fields.Char('Código de Seguridad', size=8, readonly=True, copy=False)
    emission_code = fields.Char('Tipo de Emisión', size=1, readonly=True, copy=False)
    epayment_id = fields.Many2one('account.epayment', 'Forma de Pago',copy=False)
    sent = fields.Boolean('Enviado?',copy=False)

    def get_auth(self, document):
        partner = document.company_id.partner_id
        if document._name == 'account.move':
            return document.auth_inv_id
        elif document._name == 'account.retention':
            return partner.get_authorisation('ret_in_invoice')

    def get_secuencial(self):
        return getattr(self, self._FIELDS[self._name])[6:]

    def _info_tributaria(self, document, access_key, emission_code):
        """
        """
        company = document.company_id
        auth = self.get_auth(document)
        infoTributaria = {
            'ambiente': self.env.user.company_id.env_service,
            'tipoEmision': emission_code,
            'razonSocial': company.name,
            'nombreComercial': company.name,
            'ruc': company.partner_id.identifier,
            'claveAcceso':  access_key,
            'codDoc': utils.tipoDocumento[auth.type_id.code],
            'estab': auth.serie_entidad,
            'ptoEmi': auth.serie_emision,
            'secuencial': self.get_secuencial(),
            'dirMatriz': company.street,
            'agent_ids':company.agent_ids
        }
        return infoTributaria

    def get_code(self):
        """
        this function return the sequence for einvoice
        in case that some company dont have sequence
        create the sequence
        :return code
        """
        ir_sequence = self.env['ir.sequence'].with_context(force_company=self.company_id.id)
        code = ir_sequence.next_by_code('edocuments.code')
        if code:
            return code
        return ir_sequence.sudo().create({
            'name': 'Secuencia de Facturas Electronicas {name}'.format(name=self.company_id.name),
            'company_id': self.company_id.id,
            'code': 'edocuments.code',
            'number_next_actual': 100,
            'padding': 8
        }).next_by_id()

    def get_access_key(self, name):
        if name == 'account.move':
            auth = self.company_id.partner_id.get_authorisation(getattr(self,'type'))
            # ld = self.date_invoice.split('-')
            numero = getattr(self, 'invoice_number')
            doc_date=self.invoice_date
        elif name == 'account.retention':
            auth = self.company_id.partner_id.get_authorisation('ret_in_invoice')  # noqa
            # ld = self.date.split('-')
            numero = getattr(self, 'name')
            #numero = numero[6:15]
            doc_date = self.date
        # ld.reverse()
        fecha = doc_date.strftime('%d%m%Y')
        tcomp = utils.tipoDocumento[auth.type_id.code]
        ruc = self.company_id.partner_id.identifier
        codigo_numero = self.get_code()
        tipo_emision = self.company_id.emission_code
        access_key = (
            [fecha, tcomp, ruc],
            [numero, codigo_numero, tipo_emision]
            )
        return access_key

    
    def _get_codes(self, name='account.move'):
        ak_temp = self.get_access_key(name)
        self.SriServiceObj.set_active_env(self.env.company.env_service)
        access_key = self.SriServiceObj.create_access_key(ak_temp)
        emission_code = self.company_id.emission_code
        return access_key, emission_code

    
    def check_before_sent(self):
        """
        """
        MESSAGE_SEQUENCIAL = ' '.join([
            u'Los comprobantes electrónicos deberán ser',
            u'enviados al SRI para su autorización en orden cronológico',
            'y secuencial. Por favor enviar primero el',
            ' comprobante inmediatamente anterior.'])
        FIELD = {
            'account.move': 'invoice_number',
            'account.retention': 'name',
            'account.guia.remision': 'name'
        }
        number = getattr(self, FIELD[self._name])
        sql = ' '.join([
            "SELECT autorizado_sri, %s FROM %s" % (FIELD[self._name], self._table),  # noqa
            "WHERE state='open' AND %s < '%s'" % (FIELD[self._name], number),  # noqa
            self._name == 'account.move' and "AND type = 'out_invoice'" or '',  # noqa
            "ORDER BY %s DESC LIMIT 1" % FIELD[self._name]
        ])
        self.env.cr.execute(sql)
        res = self.env.cr.fetchone()
        if not res:
            return True
        auth, number = res
        if auth is None and number:
            raise UserError(MESSAGE_SEQUENCIAL)
        return True

    def check_date(self, date_invoice):
        """
        Validar que el envío del comprobante electrónico
        se realice dentro de las 24 horas posteriores a su emisión
        """
        LIMIT_TO_SEND = 5
        MESSAGE_TIME_LIMIT = u' '.join([
            u'Los comprobantes electrónicos deben',
            u'enviarse con máximo 24h desde su emisión.']
        )
        dt = date_invoice
        days = (date.today() - dt).days
        if days > LIMIT_TO_SEND:
            raise UserError(MESSAGE_TIME_LIMIT)

    
    def update_document(self, auth, codes):
        if auth.fechaAutorizacion != '':
            fecha = auth.fechaAutorizacion.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            sri_ok = True
        else:
            fecha = None
            sri_ok = False
        self.write({
            'numero_autorizacion': auth.numeroAutorizacion,
            'estado_autorizacion': auth.estado,
            'ambiente': auth.ambiente,
            'fecha_autorizacion': fecha,  # noqa
            'autorizado_sri': sri_ok, #auth.autorizado_sri,
            'clave_acceso': codes[0],
            'emission_code': codes[1]
        })

    
    def add_attachment(self, xml_element, auth):
        buf = io.StringIO()
        buf.write(xml_element)
        document = base64.encodestring(buf.getvalue().encode())
        buf.close()
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        attach = self.env['ir.attachment'].with_context(ctx).create(
            {
                'name': '{0}.xml'.format(self.clave_acceso),
                'store_fname':'{0}.xml'.format(self.clave_acceso),
                'datas': document,
                #'datas_fname':  '{0}.xml'.format(self.clave_acceso),
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary'
            },
        )
        self.env.cr.commit()
        return attach

    
    def send_document(self, attachments=None, tmpl=False):
        self.ensure_one()
        self._logger.info('Enviando documento electronico por correo')
        tmpl = self.env.ref(tmpl)
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        if isinstance(attachments, list):
            email_values={'attachment_ids': [(4,int(a.id)) for a in attachments]}
        else:
            email_values={'attachment_ids': [(4,int(attachments.id)),]}
        tmpl.with_context(ctx).send_mail(  # noqa
            self.id,
           email_values=email_values
        )
        self.sent = True
        return True

    def render_document(self, document, access_key, emission_code):
        pass
