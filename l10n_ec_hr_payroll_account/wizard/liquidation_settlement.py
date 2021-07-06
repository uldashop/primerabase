# -*- coding: utf-8 -*-
from odoo import api, fields, _, models
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta
import datetime

class liquidationSettlemnet(models.TransientModel):
    _inherit = 'report.liq_settlement'

    def delete_payslip(self):
        if self.payslip_id and not self.pay_id:
            self.payslip_id.state = "draft"
            self.payslip_id.unlink()
        return " "

    def print_settlement(self):
        obj_payslip = self.env['hr.payslip']
        date_c = self.date_end
        date_end = date_c.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)
        date_init = date_c.replace(day=1)
        payslip = obj_payslip.search([('employee_id','=',self.name.id),('date_from','=',date_init),
                ('date_to','=',date_end),('state','=','paid')])
        if not payslip:
            if self.pay_id:
                self.contract_id.date_end = date_c
            payslip = self.create_payslip_employee(date_init,date_end,self.date_end)
        payslip.state = 'draft'
        payslip.compute_sheet()
        payslip.state = 'paid'
        self.payslip_id = payslip.id
        data = self.calcule_total_expenses()
        self.state = 'done'
        self.env.cr.commit()
        if self.pay_id:
            self.generate_paid()
        return self.env.ref('l10n_ec_hr_payroll.report_hr_settlemet').report_action(self)

    def generate_paid(self):
        payment_ids = []
        obj_payment = self.env['account.payment']
        journal_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_payslip',False,self.env.company.id)
        account_debit_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_settlement',False,self.env.company.id)
        if not account_debit_id or not journal_id:
            raise ValidationError(_("Debe configurar la cuenta de fiquinito o diario de pagos en Configuraciones."))
        amount = 0.00
        total = self.calcule_total_income() - self.calcule_total_expenses()
        total = round(float(total),2)
        method_obj = self.env['account.payment.method']
        method = method_obj.search([('code','=','check_printing'),('payment_type','=','outbound')])
        if self.name.bank_account_id:
            method = method_obj.search([('code','=','transfer'),('payment_type','=','outbound')])
        if not method:
            method = method_obj.search([('code','=','manual'),('payment_type','=','outbound')])
        journal = method.id
        payment = obj_payment.create({
                'partner_type':'supplier',
                'partner_id':self.name.address_home_id.id,
                'amount': total,
                'payment_date': date.today(),
                'communication':'Pago de Liquidacion de Finiquito ' + self.name.name,
                'name':'Pago de Liquidacion de Finiquito ' + self.name.name,
                'payment_type': 'outbound',
                'account_debit_id':account_debit_id,
                'journal_id':journal_id,
                'payment_method_id': journal,
                'company_id': self.env.company.id,
                })
        if method.code == 'check_printing':
            payment._onchange_amount()

        lines = []
        for payslip in self.payslip_id.line_ids:
            if payslip.category_id.code in ('APOR','NAPOR'):
                # rule_id = self.env['hr.salary.rule'].search([('code','=',payslip.code)])
                if payslip.total != 0:
                    lines.append((0,0,
                        {
                            'ref': payslip.name,
                            'account_id': payslip.salary_rule_id.account_debit.id,
                            'credit': 0.0,
                            'amount_currency':0,
                            'debit': payslip.total,
                        }))
        amount = self.calcule_sayings('ProvDec13')
        contract_id = self.env['hr.contract'].search([('employee_id','=',self.name.id),('state','=','open')])
        if amount:
            rule_id = False
            for line in contract_id.struct_id.rule_ids:
                if line.code == 'ProvDec13':
                    rule_id = line
                    break
            lines.append((0,0,
                    {
                        'ref': 'Liquidacion de Finiquito ' + self.name.name,
                        'account_id': rule_id.account_credit.id,
                        'credit': 0.0,
                        'amount_currency':0,
                        'debit': amount *-1,
                    }))
        amount = self.calcule_sayings('ProvDec14')
        if amount:
            rule_id = False
            for line in contract_id.struct_id.rule_ids:
                if line.code == 'ProvDec14':
                    rule_id = line
                    break
            lines.append((0,0,
                    {
                        'ref': line.name,
                        'account_id': rule_id.account_credit.id,
                        'credit': 0.0,
                        'debit': amount * -1,
                        'amount_currency':0,
                    }))
        amount = self.calcule_sayings('VACACIONES')
        if amount:
            rule_id = False
            for line in contract_id.struct_id.rule_ids:
                if line.code in 'VACACIONES':
                    rule_id = line
                    break
            lines.append((0,0,
                    {
                        'ref': line.name,
                        'account_id': rule_id.account_credit.id,
                        'credit': 0.0,
                        'debit': amount *-1,
                        'amount_currency':0,
                    }))
        if self.settlement_id.code.upper() == 'INTEMPESTIVO':
            years = self.diff_year() if self.diff_year() > 3 else 3
            amount = (years * self.contract_id.wage)
            rule_id = False
            for line in contract_id.struct_id.rule_ids:
                if line.code in 'INDE':
                    rule_id = line
                    break
            lines.append((0,0,
                    {
                        'ref': rule_id.name + ' INTEMPESTIVO 100',
                        'account_id': rule_id.account_debit.id,
                        'credit': 0.0,
                        'debit': amount,
                        'amount_currency':0,
                    }))
        amount = (self.diff_year_2() * self.contract_id.wage * 0.25)
        if amount:
            rule_id = False
            for line in contract_id.struct_id.rule_ids:
                if line.code in 'INDE':
                    rule_id = line
                    break
            lines.append((0,0,
                    {
                        'ref': rule_id.name + ' INTEMPESTIVO 25',
                        'account_id': rule_id.account_debit.id,
                        'credit': 0.0,
                        'debit': amount,
                        'amount_currency':0,
                    }))

        for payslip in self.payslip_id.line_ids:
            if payslip.category_id.name in ('Descuentos','Aportes') :
                # rule_id = self.env['hr.salary.rule'].search([('code','=',payslip.code)])
                if payslip.total != 0:
                    lines.append((0, 0,
                    {
                        'ref': 'Liquidacion de Finiquito ' + self.name.name,
                        'account_id': payslip.salary_rule_id.account_debit.id,
                        'credit': abs(payslip.total),
                        'amount_currency':0,
                        'debit': 0.0
                    }))
                if payslip.code == 'IESSPAT':
                    lines.append((0, 0,
                    {
                        'ref': 'Liquidacion de Finiquito ' + self.name.name,
                        'account_id':  payslip.salary_rule_id.account_credit.id,
                        'credit': 0.0,
                        'amount_currency':0,
                        'debit': abs(payslip.total)
                    }))
        rule_id = False
        lines.append((0,0,
                    { 
                    'ref': 'Liquidacion de Finiquito ' + self.name.name,
                    'account_id': account_debit_id,
                    'credit': total,
                    'debit': 0.0,
                    'amount_currency':0,
                    }))
        acc_move_obj = self.env['account.move']
        move_data = {
                'journal_id': journal_id,
                'date': date.today(),
                'type':'entry',
                'company_id': self.env.company.id,
                }
        move_data.update({'line_ids': lines})
        acc_move_obj.create(move_data)
