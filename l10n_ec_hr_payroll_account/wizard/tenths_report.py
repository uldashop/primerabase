# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class tenthsReports(models.TransientModel):
    _inherit = "report.tenths"


    def generate_paid(self):
        dtc = []
        if not self.pay_id:
            for contract in self.contract_active():
                dtc.append(self.report_data(contract))
        else:
            payment_obj = self.env['account.payment']
            if self.name == 'ProvDec13':
                account_debit_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_xiii',False,self.env.company.id)
            else:
                account_debit_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_xiv',False,self.env.company.id)

            journal_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_payslip',False,self.env.company.id)
            method_obj = self.env['account.payment.method']
            method = method_obj.search([('code','=','check_printing'),('payment_type','=','outbound')])
            if not method:
                method = method_obj.search([('code','=','manual'),('payment_type','=','outbound')])
            check = method.id
            name = {
                'ProvDec13':' Pago Decimo Tercer Sueldo ',
                'ProvDec14':' Pago Decimo Cuarto Sueldo ',
                'utilies':' Pago de Utilidades ',
            }
            if not account_debit_id or not journal_id:
                raise ValidationError(_("Debe configurar el Cuenta de %s o Diario de Pagos en Configuraciones." % name[self.name]))
            for contract in self.contract_active():
                if contract.employee_id.bank_account_id:
                    transfer = method_obj.search([('code','=','transfer'),('payment_type','=','outbound')])
                dtc.append(self.report_data(contract))
                for line in contract.struct_id.rule_ids:
                    if line.code in self.name or self.name in line.code:
                        rule_id = line
                amount = abs(self.total_tenths(contract.employee_id))
                if amount > 0: 
                    pay =payment_obj.create({
                            'partner_type':'supplier',
                            'partner_id':contract.employee_id.address_home_id.id,
                            'amount': amount,
                            'payment_date': date.today(),
                            'communication':name[self.name] + contract.employee_id.name,
                            'name':name[self.name] + contract.employee_id.name,
                            'payment_type': 'outbound',
                            'account_debit_id':account_debit_id,
                            'journal_id': journal_id,
                            'payment_method_id': check if not contract.employee_id.bank_account_id else transfer.id,
                            'company_id': self.env.company.id,
                        })
                    if not contract.employee_id.bank_account_id and method.code == 'check_printing':
                        pay._onchange_amount()
        if dtc:
            self.report_generate(dtc)
