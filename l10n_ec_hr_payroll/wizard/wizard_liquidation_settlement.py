# -*- coding:utf-8 -*-

from odoo import api, models, fields,_
from datetime import date
import datetime
from math import ceil
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning, ValidationError

class liquidationSettlement(models.TransientModel):
    _name = 'report.liq_settlement'
    _description = 'Reporte de liquidacion de finiquito'

    name = fields.Many2one('hr.employee', string='Empleado', required=True)
    date_start = fields.Date('Fecha de Ingreso')
    date_end = fields.Date('Fecha de Salida')
    contract_id = fields.Many2one('hr.contract', string='Contrato')
    settlement_id = fields.Many2one('hr.settlement.type',string='Motivo')
    payslip_id = fields.Many2one('hr.payslip',string='Rol de Pago')
    amount = fields.Float('Indemnizacion')
    region_id = fields.Selection([('cost','Costa'),
                                ('sierra','Sierra'),
                                ('amazon','Oriente'),
                                ('island','Galapagos')],string="Region",default="cost")
    pay_id = fields.Boolean('Realizar Pago', default=False)
    state = fields.Selection([('draft','Borrador'),('done','Realizado')],'Estado',default='draft')

    @api.onchange('name')
    def _onchange_settlement(self):
        if self.name:
            obj_contract = self.env['hr.contract']
            contract = obj_contract.search([('employee_id','=',self.name.id),('state','!=','draft')], order='id asc', limit=1)
            if  contract:
                self.date_start = contract.date_start
            end_contract = obj_contract.search([('employee_id','=',self.name.id),('state','!=','draft')], order='id desc', limit=1)
            if end_contract:
                self.contract_id = end_contract.id
                if end_contract.date_end:
                    self.date_end = end_contract.date_end
                else:
                    self.date_end = date.today()
                    # self.contract_id.date_end = date.today() 

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
        payslip.state = 'done'
        self.payslip_id = payslip.id
        data = self.calcule_total_expenses()
        self.state = 'done'
        self.env.cr.commit()
        return self.env.ref('l10n_ec_hr_payroll.report_hr_settlemet').report_action(self)
    
    def delete_payslip(self):
        if self.payslip_id:
            self.payslip_id.state = "draft"
            self.payslip_id.unlink()
        return " "

    def create_payslip_employee(self,d1,d2,d3):
        obj_payslip = self.env['hr.payslip']
        date_end = d3.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)
        if d3 == date_end:
            day = 30
        else:
            day = d3.day
        if date_end.month == self.date_start.month and date_end.year == self.date_start.year:
            day -= self.date_start.day - 1
        type_id = self.env['hr.payslip.input.type'].search([('code','=','INDE')], limit=1)
        dct = {
            'employee_id': self.name.id,
            'contract_id': self.contract_id.id,
            'date_from': d1,
            'date_to': d2,
            'state': 'draft',
            'name': 'Nomina de finiquito de %s' %(self.name.name),
            'struct_id': self.contract_id.struct_id.id,
            'worked_days_line_ids':[(0,0,{
                'name':'Dias de trabajo pagados al 100%',
                'work_entry_type_id':self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                'number_of_days': day,
                'number_of_hours': day * 8,
                'contract_id':self.contract_id.id,
            })],
            'input_line_ids':[(0,0,{
                'name':'Indemnizacion de mutuo acuerdo',
                'amount': self.amount,
                'input_type_id':type_id.id,
                'contract_id': self.contract_id.id,
            })],
        }
        payslip = obj_payslip.create(dct)
        return payslip


    def calcule_total_expenses(self):
        return sum([abs(l.total) for l in self.payslip_id.line_ids if l.category_id.name == 'Descuentos' or l.code == 'IESSPER'])

    def calcule_XIV_date(self):
        anio = int(self.date_end.strftime('%Y'))
        if self.region_id in ('cost','island'):
            if self.date_end.month > 2:
                date_init = date(anio,3,1)
                date_end = self.date_end.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)
            else:
                
                date_init = date(anio-1,3,1)
                if anio%4 == 0 and anio%100 != 0 or anio%400 == 0:
                    date_end = date(anio,2,29)
                else:
                    date_end = date(anio,2,28)
        else:
            if self.date_end.month > 6:
                date_init = date(anio,7,1)
                date_end = date(anio+1,6,30)
            else:
                date_init = date(anio-1,7,1)
                date_end = date(anio,6,30)

        return date_init,date_end

    def calcule_XIII_date(self):
        if self.date_end.month == 12 :
            anio = self.date_end.strftime('%Y')
            date_init = date(anio,12,1)
            date_end = date(anio,12,31)
        else:
            anio = int(self.date_end.strftime('%Y'))
            date_init = date(anio-1,12,1)
            date_end = self.date_end.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)
        return date_init,date_end


    def calcule_sayings(self, provision):
        obj_payslip = self.env['hr.payslip']
        value = 0.00
        if provision == 'ProvDec13':
            date_init,date_end = self.calcule_XIII_date()
        elif provision == 'ProvDec14':
            date_init,date_end = self.calcule_XIV_date()
        else:
            if self.date_start.month <= self.date_end.month:
                year = self.date_end.year
            else:
                year = self.date_end.year - 1

            date_init = date(year,self.date_start.month,1)
            date_end = self.date_end.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)

        payslip_ids = obj_payslip.search([('employee_id','=',self.name.id),
                                        ('date_from','>=',date_init),
                                        ('date_to','<=',date_end),
                                        ('state','=','paid')])
        for payslip in payslip_ids:
            if provision == 'VACACIONES':
                total = [line.total for line in payslip.line_ids if line.code in provision][0]
                date_start = date(date_init.year,date_init.month, self.date_start.day)
                if payslip.date_from < date_start and int(31 - self.date_start.day) < payslip.worked_days_line_ids[0].number_of_days:
                    value += ((total / payslip.worked_days_line_ids[0].number_of_days) * int(31 - self.date_start.day))
                # elif payslip.date_to > self.date_end and int(self.date_end.day) < 30:
                #     amount += abs((total/ payslip.worked_days_line_ids[0].number_of_days) * int(self.date_end.day))
                else:
                    value += (total)
            else:
                value += sum([line.total for line in payslip.line_ids if line.code in provision])
        return value

    def diff_year(self):
        return ceil((self.date_end - self.date_start).days/365.2425)

    def diff_year_2(self):
        return int((self.date_end - self.date_start).days/365.2425)

    def calcule_total_income(self):
        amount = sum([l.total for l in self.payslip_id.line_ids if l.category_id.code in ('APOR','NAPOR')])
        # amount += self.amount
        years = self.diff_year() if self.diff_year() > 3 else 3
        if self.settlement_id.code.upper() == 'INTEMPESTIVO':
            amount += (years * self.contract_id.wage)
        amount += (self.diff_year_2() * self.contract_id.wage * 0.25)
        amount -= self.calcule_sayings('ProvDec13')
        amount -= self.calcule_sayings('ProvDec14')
        amount -= self.calcule_sayings('VACACIONES')
        return amount