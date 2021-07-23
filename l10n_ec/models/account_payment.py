# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import os
import logging
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
from odoo.addons.account.models.account_payment import account_payment as account_payment_orig

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
    'liq_purchase': 'supplier',
    'sale_note': 'customer',
    'in_debit': 'supplier',
    'out_debit': 'customer',
}

type_account = {
    'savings': 'AHO',
    'checking': 'CTE',
}

type_ident = {
    'cedula': 'C',
    'ruc': 'R',
    'pasaporte':'P',
}

    

class account_payment(models.Model):
    _name = "account.payment"
    _inherit = "account.payment"
    _description = "Payments"
    _order = "payment_date desc, name desc"

    communication = fields.Char(string='Memo', required=True)
    report_bank = fields.Binary(string='Archivo Bancario', readonly=True)
    report_bank_name = fields.Char(string='Nombre Archivo Bancario', store=True)
    account_debit_id = fields.Many2one('account.account', string="Cuenta de Debito")
    sequence_report = fields.Integer('N. Comprobante')

    def report_disbursement(self):
        move_ids = []
        invoice_ids = []
        payment_ids = self.env['account.payment'].browse(self._ids)
        sequence_id = self.env['ir.sequence']
        payment_method_id = ''
        partner_id = ''
        check_number = ''
        payment_date = ''
        payment_type = ''
        partner_type = ''
        communication = ''
        journal = ''
        currency_id = ''
        amount = 0
        sequence = ''
        for payment in payment_ids:
            if payment.sequence_report:
                sequence = payment.sequence_report
            amount += payment.amount
            if payment.check_number:
                check_number += str(payment.check_number) + '/ '
            if not partner_id:
                partner_id = payment.partner_id.name
                payment_method_id = {'code':payment.payment_method_id.code,'name':payment.payment_method_id.name}
                payment_date = payment.payment_date
                payment_type = payment.payment_type
                partner_type = payment.partner_type
                communication = payment.communication
                journal = payment.journal_id.name
                currency_id = payment.currency_id
            if payment.payment_method_id.code != payment_method_id['code'] or partner_id != payment.partner_id.name:
                raise ValidationError(_('Debe seleccionar pagos con el mismo método de pago, cliente o proveedor'))
            for invoice in payment.reconciled_invoice_ids:
                invoice_ids.append({
                    'invoice_date':invoice.invoice_date,
                    'number':invoice.invoice_number,
                    'amount_total': invoice.amount_total,
                    'payment': payment._get_invoice_payment_amount(invoice),
                    'residual': invoice.amount_residual,
                })
            for move in payment.move_line_ids:
                move_ids.append({
                    'account_id':move.account_id,
                    'name': move.name,
                    'debit': move.debit,
                    'credit': move.credit,
                })
        if payment_type == 'outbound' and not sequence:
            sequence =  sequence_id.next_by_code('comprobante_egreso')
        elif payment_type == 'inbound' and not sequence:
            sequence =  sequence_id.next_by_code('comprobante_ingreso')
        payment_ids.write({'sequence_report': sequence})
        data = {
            'payment_date': payment_date,
            'partner_type': partner_type,
            'amount': amount,
            'communication': communication,
            'journal_id': journal,
            'reconciled_invoice_ids': invoice_ids,
            'move_line_ids': move_ids,
            'partner_id': partner_id,
            'check_number': check_number,
            'payment_method_id': payment_method_id,
            'payment_type': payment_type,
            'currency_id':currency_id,
            'sequence':sequence,
        }
        return data

    def report_bank_transfer(self):
        bank_id = self.env['res.partner.bank'].search([('partner_id','=',self.partner_id.id)],order="id desc", limit=1)
        if not bank_id:
            raise ValidationError(_("%s no tiene registrada una cuenta bancaria." % (self.partner_id.name)))
        dtc = []
        data = {'employees':''}
        dtc.append({
            'identifier':self.partner_id.identifier,
            'amount':'%.2f'%(self.amount),
            'type_account':type_account[bank_id.account_type],
            'account_number':bank_id.acc_number,
            'reference': self.communication or 'PAGO',
            'phone':self.partner_id.phone or self.partner_id.mobile,
            'month':self.payment_date.month,
            'year':self.payment_date.year,
            'type_identifier':type_ident[self.partner_id.type_identifier],
            'name':self.partner_id.name,
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
            self.report_bank_name = 'Transferencia Bancaria %s.txt' %(self.partner_id.name)
            return out
        else:
            raise ValidationError(_("Primero debe configurar un formato de Transferencia Bancaria en el Diario."))

    @api.model
    def default_get(self, default_fields):
        rec = super(account_payment_orig, self).default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids).filtered(lambda move: move.is_invoice(include_receipts=True))

        # Check all invoices are open
        if not invoices or any(invoice.state != 'posted' for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices"))
        # Check if, in batch payments, there are not negative invoices and positive invoices
        dtype = invoices[0].type
        for inv in invoices[1:]:
            if inv.type != dtype:
                if ((dtype == 'in_refund' and inv.type == 'in_invoice') or
                        (dtype == 'in_invoice' and inv.type == 'in_refund')):
                    raise UserError(_("You cannot register payments for vendor bills and supplier refunds at the same time."))
                if ((dtype == 'out_refund' and inv.type == 'out_invoice') or
                        (dtype == 'out_invoice' and inv.type == 'out_refund')):
                    raise UserError(_("You cannot register payments for customer invoices and credit notes at the same time."))

        amount = self._compute_payment_amount(invoices, invoices[0].currency_id, invoices[0].journal_id, rec.get('payment_date') or fields.Date.today())
        rec.update({
            'currency_id': invoices[0].currency_id.id,
            'amount': abs(amount),
            'payment_type': 'inbound' if amount > 0 else 'outbound',
            'partner_id': invoices[0].commercial_partner_id.id,
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
            'communication': invoices[0].invoice_payment_ref or invoices[0].ref or invoices[0].name,
            'invoice_ids': [(6, 0, invoices.ids)],
        })
        return rec

class payment_register(models.TransientModel):
    _name = 'account.payment.register'
    _inherit = 'account.payment.register'
    
    def _prepare_payment_vals(self, invoices):
        '''Create the payment values.

        :param invoices: The invoices/bills to pay. In case of multiple
            documents, they need to be grouped by partner, bank, journal and
            currency.
        :return: The payment values as a dictionary.
        '''
        amount = self.env['account.payment']._compute_payment_amount(invoices, invoices[0].currency_id, self.journal_id, self.payment_date)
        values = {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_date': self.payment_date,
            'communication': " ".join(i.invoice_payment_ref or i.ref or i.name for i in invoices),
            'invoice_ids': [(6, 0, invoices.ids)],
            'payment_type': ('inbound' if amount > 0 else 'outbound'),
            'amount': abs(amount),
            'currency_id': invoices[0].currency_id.id,
            'partner_id': invoices[0].commercial_partner_id.id,
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
            'partner_bank_account_id': invoices[0].invoice_partner_bank_id.id,
        }
        return values

    def get_payments_vals(self):
        '''Compute the values for payments.

        :return: a list of payment values (dictionary).
        '''
        grouped = defaultdict(lambda: self.env["account.move"])
        for inv in self.invoice_ids:
            if self.group_payment:
                grouped[(inv.commercial_partner_id, inv.currency_id, inv.invoice_partner_bank_id, MAP_INVOICE_TYPE_PARTNER_TYPE[inv.type])] += inv
            else:
                grouped[inv.id] += inv
        return [self._prepare_payment_vals(invoices) for invoices in grouped.values()]
