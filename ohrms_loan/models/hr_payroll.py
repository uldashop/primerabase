# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime
from odoo.exceptions import ValidationError


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    loan_line_id = fields.Many2one('hr.loan.line', string="Loan Installment")


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_inputs_line(self,contracts,date_from,date_to):
        loan_id = self.env.ref('ohrms_loan.input_loan')
        self.input_line_ids = []
        res = []
        for contract in contracts:
            inputs_ids = self.env['hr.input'].search([('company_id','=',self.env.company.id),
                                    ('date','<=',date_to),('date','>=',date_from),
                                    ('employee_id','=',contract.employee_id.id),('state','=',True)])
            for inputs in inputs_ids:
                input_data = {
                    'name': inputs.input_type_id.name,
                    'input_type_id': inputs.input_type_id.id,
                    'code': inputs.input_type_id.code,
                    'contract_id': contract.id,
                    'amount': inputs.amount,
                    'input_id': inputs.id,
                    'payslip_id':self.id,
                }
                res.append(input_data)
            loan_ids = self.env['hr.loan.line'].search([
                                    ('date','<=',date_to),('date','>=',date_from),
                                    ('employee_id','=',contract.employee_id.id),('paid','=',False)])
            for loan in loan_ids:
                input_data = {
                    'name': loan.loan_id.name,
                    'input_type_id': loan_id.id,
                    'code':loan_id.code,
                    'contract_id': contract.id,
                    'amount': loan.amount,
                    'loan_line_id': loan.id,
                    'payslip_id':self.id,
                }
                res.append(input_data)
        return res

    def action_payslip_done(self):
        for payslip in self:
            for line in payslip.input_line_ids:
                if line.loan_line_id:
                    line.loan_line_id.paid = True
        super(HrPayslip,self).action_payslip_done()