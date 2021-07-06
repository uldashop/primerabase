# -*- coding:utf-8 -*-

from odoo import api, models, fields,_
from datetime import date, timedelta
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning, ValidationError

class reportVacation(models.TransientModel):
    _name = 'report.liq_vacation'
    _description = 'Reporte de liquidacion de vacaciones'

    def compute_employee(self):
        employee = 0
        employee_ids = []
        day = []
        contract_ids = self.env['hr.contract'].search(['|',('date_end','=',None),('date_start','<',date.today()),('state','not in',('draft','cancel'))], order="employee_id,date_start asc")
        for contract in contract_ids:
            if employee != contract.employee_id.id:
                employee = contract.employee_id.id
                year = 0
            else:
                if (contract.date_start - date_end).days > 1:
                    year = 0
            if contract.date_end:
                date_end = contract.date_end
            else:
                date_end = date.today()
            year += (date_end - contract.date_start).days
            day.append(year)
            if year >= 365:
                employee_ids.append(contract.employee_id.id)
        return [('id','in',employee_ids)]

    name = fields.Many2one('hr.employee',string='Empleado', domain=compute_employee, required=True)
    date_start = fields.Date('Fecha Inicio', required=True)
    date_end = fields.Date('Fecha Corte', required=True, default = date.today())
    contract_id = fields.Many2one('hr.contract',string='Contrato')
    pay_id = fields.Boolean('Realizar Pago', default=False)
    state = fields.Selection([('draft','Borrador'),('done','Realizado')],'Estado',default='draft')


    @api.onchange('date_start','name','date_end')
    def onchange_date_start(self):
        if self.name and self.date_start:
            obj_contract = self.env['hr.contract']
            contract = obj_contract.search([('employee_id','=',self.name.id),('active','=',True)])
            if contract:
                self.contract_id = contract.id
                self.date_start = str(self.date_start.year) + str(contract.date_start)[4:10]
                date_start = date(self.date_start.year+1,self.date_start.month,self.date_start.day)
                date_end = date_start+datetime.timedelta(days=-1)
                if date.today() < date_end:
                    self.date_end = date.today()
                else:
                    self.date_end = date_end

    def calcule_total_vacation(self,payslip_id):
        amount = 0 
        for payslip in payslip_id:
            if payslip.date_to >= self.date_start and payslip.date_from <= self.date_end and payslip.state == 'paid':
                for line in payslip.line_ids:
                    if line.code in 'VACACIONES':
                        if payslip.date_from < self.date_start and int(31 - self.date_start.day) < payslip.worked_days_line_ids[0].number_of_days:
                            amount += abs((line.amount / payslip.worked_days_line_ids[0].number_of_days) * int(31 - self.date_start.day))
                        elif payslip.date_to > self.date_end and int(self.date_end.day) < 30:
                            amount += abs((line.amount/ payslip.worked_days_line_ids[0].number_of_days) * int(self.date_end.day))
                        else:
                            amount += abs(line.amount)
        return amount

    def print_liquidation(self):
        self.state = 'done'
        self.generate_paid()
        return self.env.ref('l10n_ec_hr_payroll.hr_vacations_report').report_action(self)


    def calcule_days(self):
        # if self.date_start.month <= self.date_end.month:
        #     year = str(self.date_end.year)
        # else:
        #     year = str(self.date_end.year - 1)

        # date_init = date(int(year),self.date_start.month,self.date_start.day)
        # date_end = self.date_end
        days = int((self.date_end - self.date_start).days * (15/365))
        return days


    def generate_paid(self):
        pass