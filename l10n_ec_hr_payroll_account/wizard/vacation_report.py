# -*- coding:utf-8 -*-

from odoo import api, models, fields,_
from datetime import date
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning, ValidationError

class reportVacation(models.TransientModel):
    _inherit = 'report.liq_vacation'

    def generate_paid(self):
        if self.pay_id:
            payment_ids = []
            payment_obj = self.env['account.payment']
            # obj_payment = self.env['account.batch.payment']
            rule_id = self.env['hr.salary.rule'].search([('code','=','VACACIONES')])
            amount = 0.00
            # journal_id = self.env['account.journal'].search([('code','=','vctn')])
            journal_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_payslip',False,self.env.company.id)
            account_debit_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_vacation',False,self.env.company.id)
            if not account_debit_id or not journal_id:
                raise ValidationError(_("Debe configurar la cuenta de pago de vacaciones o diario de pagos en Configuraciones."))
            for payroll in self.name.slip_ids:
                if payroll.date_to >= self.date_start and payroll.date_from <= self.date_end and payroll.state == 'paid':
                    amount += self.calcule_total_vacation(payroll)
            
            method_obj = self.env['account.payment.method']
            method = method_obj.search([('code','=','check_printing'),('payment_type','=','outbound')])
            if self.name.bank_account_id:
                method = method_obj.search([('code','=','transfer'),('payment_type','=','outbound')])
            if not method:
                method = method_obj.search([('code','=','manual'),('payment_type','=','outbound')])
            journal = method.id
            pay = payment_obj.create({
                    'partner_type':'supplier',
                    'partner_id':self.name.address_home_id.id,
                    'amount': amount,
                    'payment_date': date.today(),
                    'communication':'Pago de Vacaciones ' + self.name.name,
                    'name':'Pago de Vacaciones ' + self.name.name,
                    'payment_type': 'outbound',
                    'account_debit_id':account_debit_id,
                    'payment_method_id': journal,
                    'journal_id': journal_id,
                    'company_id': self.env.company.id,
                })
            if method.code == 'check_printing':
                pay._onchange_amount()
            # lines =[]
            # lines.append((0, 0,
            #     {
                    
            #         'ref': 'Liquidacion de vacaciones ' + self.name.name,
            #         'account_id': rule_id.account_credit.id,
            #         'credit': amount,
            #         'amount_currency':0,
            #         'debit': 0.0
            #     }))
                    
            # lines.append((0,0,
            #     {
                    
            #         'ref': 'Liquidacion de vacaciones ' + self.name.name,
            #         'account_id': journal_id.default_debit_account_id.id,
            #         'credit': 0.0,
            #         'debit': amount,
            #         'amount_currency':0,
            #     }))
            # acc_move_obj = self.env['account.move']
            # move_data = {
            #         'journal_id': journal_id,
            #         'date': date.today(),
            #         'type':'entry',
            #         }
            # move_data.update({'line_ids': lines})