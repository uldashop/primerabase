# -*- coding: utf-8 -*-
from odoo import _,api,fields,models
from odoo.exceptions import (
    Warning as UserError,
    ValidationError
)
from datetime import date, datetime, time, timedelta

type_doc = {
    'week': 'Semanal',
    'fortnight': 'Quincenal',
}

class WizardPayFortnight(models.TransientModel):
    _inherit = "wizard.hr.fortnight"

    journal_id = fields.Many2one(string="Diario", comodel_name='account.journal',default=lambda self: self.env['ir.default'].sudo().get("res.config.settings",'journal_fortnight',False,self.env.company.id))

    def create_account_move(self, lines):
        acc_move_obj = self.env['account.move']
        move_data = {
                'journal_id': self.journal_id.id,
                'date': self.date_to,
                'type':'entry',
                'company_id': self.env.company.id,
                'line_ids': lines
                }
        if lines:
            acc_move_obj.create(move_data)

    def generate_account_move_line(self,employee, line, inputs, lines, amount):
        lines.append((0,0,
            {
                'ref': 'Pago %s correspondiente al periodo desde %s hasta %s' % (type_doc[self.payment_type],str(self.date_from), str(self.date_to)),
                'account_id': self.journal_id.default_debit_account_id.id,
                'partner_id': employee.address_home_id.id,
                'credit': 0.0,
                'debit': amount if amount > 0 else (line.amount * inputs.percent /100),
                'date': self.date_to,
                'name': _("Fortnight") if amount > 0 else inputs.input_type_id.name,
                'amount_currency':0,
            }))
        lines.append((0, 0,
            {
                'ref': 'Pago %s correspondiente al periodo desde %s hasta %s' % (type_doc[self.payment_type],str(self.date_from), str(self.date_to)),
                'account_id': inputs.input_type_id.account_id.id if inputs else self.journal_id.default_credit_account_id.id,
                'partner_id': employee.address_home_id.id,
                'credit': amount if amount else (line.amount * inputs.percent /100),
                'date': self.date_to,
                'name': _("Fortnight") if amount else inputs.input_type_id.name,
                'amount_currency':0,
                'debit': 0.0
            }))
        return lines

    def create_payment(self, employee, amount, journal_pay):
        account_debit_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_fortnight_pay',False,self.company_id.id)
        if not account_debit_id:
            raise ValidationError(_("Primero debe configurar la cuenta de pago de anticipos en Configuraciones"))
        obj_payment = self.env['account.payment']
        method_obj = self.env['account.payment.method']
        method = method_obj.search([('code','=','check_printing'),('payment_type','=','outbound')])
        if employee.bank_account_id:
            method = method_obj.search([('code','=','transfer'),('payment_type','=','outbound')])
        if not method:
            method = method_obj.search([('code','=','manual'),('payment_type','=','outbound')])
        check = method.id
        pay = obj_payment.create({
            'partner_type':'supplier',
            'partner_id':employee.address_home_id.id,
            'amount': amount,
            'payment_date': date.today(),
            'communication':'Pago %s de %s correspondiente al periodo desde %s hasta %s' %(type_doc[self.payment_type],employee.name,str(self.date_from), str(self.date_to)),
            'name':'Pago %s de %s correspondiente al periodo desde %s hasta %s' %(type_doc[self.payment_type],employee.name,str(self.date_from), str(self.date_to)),
            'payment_type': 'outbound',
            'journal_id':journal_pay,
            'account_debit_id':account_debit_id,
            'payment_method_id': check,
            'company_id': self.env.company.id,
            })
        if method.code == 'check_printing':
            pay._onchange_amount()

    def validate_journal(self):
        return self.env['ir.default'].sudo().get("res.config.settings",'journal_payslip',False,self.company_id.id)

    def payment_generate(self, employee, amount):
        return {
            'employee_id': employee.id,
            'amount': amount,
            'journal_id': self.journal_id.id,
            'date_from':self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'name': 'Pago %s correspondiente al periodo desde %s hasta %s' % (type_doc[self.payment_type],str(self.date_from), str(self.date_to)),
            }