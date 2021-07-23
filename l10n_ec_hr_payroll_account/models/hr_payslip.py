# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class hrPayslip(models.Model):
    _name = "hr.payslip"
    _inherit = "hr.payslip"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('paid', 'Pagado'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")


class hrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('close', 'Done'),
        ('paid', 'Pagado'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')


    def action_paid(self):
        payment_obj = self.env['account.payment']
        journal_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_payslip',False,self.env.company.id)
        account_debit_id = self.env['ir.default'].sudo().get("res.config.settings",'journal_payroll_pay',False,self.env.company.id)
        if not account_debit_id and not journal_id:
            raise ValidationError(_("Debe configurar la cuenta de pago de nomina o diario de pagos en Configuraciones."))
        method_obj = self.env['account.payment.method']
        method = method_obj.search([('code','=','check_printing'),('payment_type','=','outbound')])
        if not method:
            method = method_obj.search([('code','=','manual'),('payment_type','=','outbound')])
        check = method.id
        for payslip in self.slip_ids:
            if payslip.employee_id.bank_account_id:
                transfer = method_obj.search([('code','=','transfer'),('payment_type','=','outbound')])
            # # Realiza la actualizacion del valor descontado en cada entrada.
            # for inputs in payslip.input_line_ids:
            #     inputs.lines_id.total_discount = inputs.amount
            for line in payslip.line_ids:
                if line.code == 'NET':
                    amount = line.total
            payslip.state = 'paid'
            payment = payment_obj.create({
                    'partner_type':'supplier',
                    'partner_id':payslip.employee_id.address_home_id.id,
                    'amount': amount,
                    'payment_date': payslip.date_to,
                    'communication':payslip.name,
                    'name':'Pago de %s' %(payslip.name),
                    'payment_type': 'outbound',
                    'account_debit_id':account_debit_id,
                    'journal_id':journal_id,
                    'payment_method_id': check if not payslip.employee_id.bank_account_id else transfer.id,
                })
            if not payslip.employee_id.bank_account_id and method.code == 'check_printing':
                payment._onchange_amount()
        self.state = 'paid'
        self.slip_ids[0].move_id.post()
