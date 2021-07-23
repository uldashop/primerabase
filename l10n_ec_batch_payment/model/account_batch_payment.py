# -*- encoding utf-8 -*-

from odoo import _, api, fields, models
import base64
import io
import os
import logging
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
from odoo.exceptions import UserError, ValidationError

type_account = {
    'savings': 'AHO',
    'checking': 'CTE',
}

type_ident = {
    'cedula': 'C',
    'ruc': 'R',
    'pasaporte':'P',
}

class accountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    report_bank = fields.Binary(string='Archivo Bancario', readonly=True)
    report_bank_name = fields.Char(string='Nombre Archivo Bancario', store=True)
    payment_method_code = fields.Char(string='Metodo de Pago',compute="payment_method_id.code")

    def report_bank_transfer(self):
        dtc = []
        data = {'employees':''}
        for payment in self.payment_ids:
            partner = payment.partner_id
            bank_ids = self.env['res.partner.bank'].search([('partner_id','=',partner.id)])
            if not bank_ids:
                raise ValidationError(_("%s no tiene registrada una cuenta bancaria." % (partner.name)))
            bank_id = bank_ids[0]
            if bank_id:
                dtc.append({
                    'identifier':partner.identifier,
                    'amount':'%.2f'%(payment.amount),
                    'type_account':type_account[bank_id.account_type],
                    'account_number':bank_id.acc_number,
                    'reference': payment.communication or 'PAGO',
                    'phone':partner.phone or partner.mobile,
                    'month':payment.payment_date.month,
                    'year':payment.payment_date.year,
                    'type_identifier':type_ident[partner.type_identifier],
                    'name':partner.name,
                    'code':bank_id.bank_id.bic,
                })
        if not dtc:
            raise ValidationError(_("Ninguno de los empleados tiene asignada una cuenta bancaria."))
        data = {'employees':dtc}
        if self.journal_id.format_transfer_id:
            tmpl_path = os.path.join(os.path.dirname(__file__), 'template')
            env = Environment(loader=FileSystemLoader(tmpl_path))
            format_report = env.get_template(self.journal_id.format_transfer_id+'.xml')
            report = format_report.render(data)
            buf = io.StringIO()
            buf.write(report)
            out = base64.encodestring(buf.getvalue().encode('utf-8')).decode()
            logging.error(out)
            buf.close()
            self.report_bank = out
            self.report_bank_name = 'Transferencia %s.txt' % (self.journal_id.name)
            return out
        else:
            raise ValidationError(_("Primero debe configurar un formato de Transferencia Bancaria en el Diario."))