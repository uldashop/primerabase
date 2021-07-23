# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import base64
from itertools import groupby
import io
import os
import logging
from jinja2 import Environment, FileSystemLoader

gender_resume = {
    'male':'M',
    'female': 'F',
}

alphabet = {
    '2':'A',
    '3':'B',
    '4':'C',
    '5':'D',
    '6':'E',
    '7':'F',
    '8':'G',
    '9':'H',
    '10':'I',
    '11':'J',
    '12':'K',
    '13':'L',
    '14':'M',
    '15':'N',
    '16':'O',
    '17':'P',
}

class tenths_reports(models.TransientModel):
    _name = "report.tenths"
    _description = _("This object is for print the thirteenth and fourteenth salary")

    def _calcule_period(self):
        year = date.today().year 
        result = []
        for line in range(10):
            result.append((year,year))
            year -= 1
        return result

    name = fields.Selection([('ProvDec13','Décimo Tercero'),
                            ('ProvDec14','Décimo Cuarto'),
                            ('utilies','Utilidades')], string="Provision", default="ProvDec13")
    period = fields.Selection(_calcule_period, string="Periodo")
    region_id = fields.Selection([('cost','Costa'),
                                ('sierra','Sierra'),
                                ('amazon','Oriente'),
                                ('island','Galapagos')],string="Region",default="cost")
    date_from = fields.Date('Fecha Inicio', compute="_compute_date_range")
    date_to = fields.Date('Fecha Fin', compute="_compute_date_range")
    pay_id = fields.Boolean('Realizar Pago', default=False)
    state = fields.Selection([('draft','Borrador'),('done','Realizado')],'Estado',default='draft')
    attachment = fields.Binary(string="Archivo MSUT", readonly=True)
    attachment_name = fields.Char(string="Nombre del Doc.", store=True)

    def report_generate(self, dct):
        data = {'employees':dct}
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        format_report = env.get_template(self.name+'.xml')
        report = format_report.render(data)
        buf = io.StringIO()
        buf.write(report)
        out = base64.encodestring(buf.getvalue().encode('utf-8')).decode()
        logging.error(out)
        buf.close()
        self.attachment = out
        if self.name == 'ProvDec13':
            self.attachment_name = 'Pago Decimo Tercer Sueldo %s.csv' %(self.period)
        elif self.name == 'ProvDec14':
            self.attachment_name = 'Pago Decimo Cuarto Sueldo %s.csv' %(self.period)


    @api.onchange('name','region_id','period')
    def _compute_date_range(self):
        if self.period:
            date_c = date(int(self.period)+1,2,28)
            period_prev = int(self.period)-1
            period_next = int(self.period)+1
            period = int(self.period)
            if self.name == 'ProvDec13':
                self.date_from = date(period_prev,12,1)
                self.date_to = date(period,11,30)
            elif self.name == 'utilies':
                self.date_from = date(period,1,1)
                self.date_to = date(period,12,31)
            elif self.region_id in ('cost','island'):
                self.date_from = date(period,3,1)
                date_end = date_c.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)
                self.date_to = date_end
            else:
                self.date_from = date(period,8,1)
                self.date_to = date(period_next,7,31)

    def range_month(self):
        if self.name == 'ProvDec13':
            return [12,1,2,3,4,5,6,7,8,9,10,11]
        elif self.name == 'utilies':
            return [1,2,3,4,5,6,7,8,9,10,11,12]
        elif self.region_id in ('cost','island'):
            return [3,4,5,6,7,8,9,10,11,12,1,2]
        else:
            return [8,9,10,11,12,1,2,3,4,5,6,7]


    def payslip_in_period(self,date_from,employee,name=""):
        obj_paylip = self.env['hr.payslip']
        days = 15 if employee.schedule_pay == 'bi-monthly' else 7
        cont = 1
        value = 0.00
        while (cont <= 30):
            payslip = obj_paylip.search([('date_from','<=',date_from),
                                    ('date_to','>=',date_from),
                                    ('employee_id','=',employee.id),
                                    ('state','=','paid')])
            if employee.schedule_pay == 'monthly':
                cont = 31
            else:
                cont += days
                if cont < 31:
                    date_from = date(date_from.year,date_from.month,cont)
            if not name:
                name = self.name
            if name in ['Dec13','Dec14']:
                for line in payslip.line_ids:
                    if line.code in name.upper() or name in line.code:
                        value += line.total
                        break
            else:
                for line in payslip.line_ids:
                    if line.code in name:
                        value += line.total
                        break
        return abs(value)


    def period_range(self,year,month):
        date_from = date(int(year),int(month),1)
        return date_from


    def contract_active(self):
        obj_contract = self.env['hr.contract']
        contract_ids = obj_contract.search([('state','=','open')])
        return contract_ids


    def print_tenth(self):
        self.generate_paid()
        self.state = 'done'
        if self.name == 'utilies':
            return self.env.ref('l10n_ec_hr_payroll.report_utilies').report_action(self)
        return self.env.ref('l10n_ec_hr_payroll.report_tenths').report_action(self)
    

    def month_in_letter(self):
        result = [
            'ENERO',
            'FEBRERO',
            'MARZO',
            'ABRIL',
            'MAYO',
            'JUNIO',
            'JULIO',
            'AGOSTO',
            'SEPTIEMBRE',
            'OCTUBRE',
            'NOVIEMBRE',
            'DICIEMBRE'
        ]
        return result


    def total_tenths(self, employee, name=""):
        if not name:
            name = self.name
        month_ids = self.range_month()
        year = int(self.period)
        value = 0.00
        for month in month_ids:
            if name in 'ProvDec13' and str(month) == '12':
                date = self.period_range(str(year - 1),month)
            elif name in 'ProvDec14' and int(month) < 3 and self.region_id in ('cost','island'):
                date = self.period_range(str(year + 1),month)
            elif name in 'ProvDec14' and int(month) < 7 and self.region_id in ('sierra','amazon'):
                date = self.period_range(str(year + 1),month)
            else:
                date = self.period_range(str(year),month)
            value += self.payslip_in_period(date,employee,name)
        return round(value,2)


    def family_count(self,employee):
        count = 0
        for line in employee.fam_ids:
            count += 1
        return count
    
    def days_report(self, employee, name=""):
        if not name:
            name = self.name
        month_ids = self.range_month()
        year = int(self.period)
        value = 0.00
        for month in month_ids:
            if name in 'ProvDec13' and str(month) == '12':
                date_from = self.period_range(str(year - 1),month)
            elif name in 'ProvDec14' and int(month) < 3 and self.region_id in ('cost','island'):
                date_from = self.period_range(str(year + 1),month)
            elif name in 'ProvDec14' and int(month) < 7 and self.region_id in ('sierra','amazon'):
                date_from = self.period_range(str(year + 1),month)
            else:
                date_from = self.period_range(str(year),month)
            obj_paylip = self.env['hr.payslip']
            days = 15 if employee.schedule_pay == 'bi-monthly' else 7
            cont = 1
            while (cont <= 30):
                payslip = obj_paylip.search([('date_from','<=',date_from),
                                            ('date_to','>=',date_from),
                                            ('employee_id','=',employee.id),
                                            ('state','=','paid')])
                if employee.schedule_pay == 'monthly':
                    cont = 31
                else:
                    cont += days
                    if cont < 31:
                        date_from = date(date_from.year,date_from.month,cont)
                if not name:
                    name = self.name
                for line in payslip.worked_days_line_ids:
                    if line.code != 'FALTAS':
                        value += line.number_of_days
        return value


    def report_data(self,contract):
        if self.name == 'ProvDec13':
            mensualize = 'X' if contract.employee_id.mensualize_13 else ' '
        elif self.name == 'ProvDec14':
            mensualize = 'X' if contract.employee_id.mensualize_14 else ' '
        amount = self.total_tenths(contract.employee_id, self.name.replace('Prov',''))
        days = self.days_report(contract.employee_id)
        number = len(self.env['hr.contract'].search([('employee_id','=',contract.employee_id.id),('state','!=','draft')]))
        if number == 1:
            identifier = ('#UIO' + contract.employee_id.visa_no) if contract.employee_id.visa_no else contract.employee_id.identification_id
        else:
            identifier = '#' + (('UIO' + contract.employee_id.visa_no) if contract.employee_id.visa_no else contract.employee_id.identification_id) + alphabet[str(number)]
        if amount:
            #======Report MSUT======
            return {
                'identifier': identifier,
                'firstname':contract.employee_id.firstname,
                'lastname':contract.employee_id.lastname,
                'gender':gender_resume[contract.employee_id.gender],
                'ocupation': contract.sectoral_id.code,
                'amount': amount,
                'days': days,
                'payment':'A' if contract.employee_id.bank_account_id else 'P',
                'partime':'X' if contract.contract_type_id.name == 'Jornada Parcial Permanente' else ' ',
                'hours_partime': contract.resource_calendar_id.hours_per_day * 5 if contract.contract_type_id.name == 'Jornada Parcial Permanente' else ' ',
                'sick':'X' if contract.employee_id.disable else ' ',
                'retention': ' ' if contract.employee_id.disable else ' ', # Verificar de donde o como se calcula este valor
                'mensualize': mensualize,
            }
            #======End Report MSUT=======
        return

    def generate_paid(self):
        dtc = []
        for contract in self.contract_active():
            dtc.append(self.report_data(contract))
        if dtc:
            self.report_generate(dtc)
