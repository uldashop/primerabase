# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import date, datetime, timedelta, time
from odoo.exceptions import ValidationError
from odoo.tools import float_round, float_repr, DEFAULT_SERVER_DATE_FORMAT
from pytz import timezone
from dateutil.relativedelta import relativedelta
import xlsxwriter
from io import BytesIO
import base64

class hrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input.type'

    type = fields.Selection([('income','Income'),('expense','Expense')], string="Type", required=True, default="income")

class hrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    input_id = fields.Many2one("hr.input", "Input/Expense")


class hrInput(models.Model):
    _name = 'hr.input'
    _description = "Payroll News"

    date = fields.Date(string="Date", default= date.today())
    employee_id = fields.Many2one('hr.employee', string="Employee")
    identification = fields.Char('Identification')
    name = fields.Char(related='input_type_id.name', string="Name", readonly=True)
    input_type_id = fields.Many2one('hr.payslip.input.type', string='Input/Expense', required=True)
    amount = fields.Float(sring="Amount")
    total_discount = fields.Float('Accumulated')
    state = fields.Boolean("Active", default="True")
    amount_unpaid = fields.Float(compute="compute_amount_unpaid",string="Balance")
    company_id = fields.Many2one("res.company","Company",default=lambda self:self.env.company.id)
    advance_id = fields.Many2one("wizard.hr.fortnight","Anticipo",store=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('identification'):
                employee = self.env['hr.employee'].search(['|',('identification_id','=',vals['identification']),('passport_id','=',vals['identification'])], limit=1)
                if not employee:
                    raise ValidationError(_("There is no employee with this identification %s" %(vals['identification'])))
                vals['employee_id'] = employee.id
        return super(hrInput, self).create(vals)

    @api.depends('amount','total_discount')
    def compute_amount_unpaid(self):
        for line in self:
            line.amount_unpaid = line.amount - line.total_discount

    @api.constrains('total_discount')
    def constraint_discount(self):
        if self.total_discount == self.amount:
            self.state = False
        if self.total_discount > self.amount:
            raise ValidationError(_('The amount entered exceeds the outstanding balance'))


class hrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_inputs_line(self,contracts,date_from,date_to):
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
        return res

    def _get_worked_day_lines(self):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        if contract.resource_calendar_id:
            paid_amount = self._get_contract_wage()
            unpaid_work_entry_types = self.struct_id.unpaid_work_entry_type_ids.ids

            work_hours = contract._get_work_hours(self.date_from, self.date_to)
            total_hours = sum(work_hours.values()) or 1
            work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
            biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
            add_days_rounding = 0
            for work_entry_type_id, hours in work_hours_ordered:
                work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
                is_paid = work_entry_type_id not in unpaid_work_entry_types
                calendar = contract.resource_calendar_id
                days = round(hours / calendar.hours_per_day, 5) if calendar.hours_per_day else 0
                if work_entry_type_id == biggest_work:
                    days += add_days_rounding
                day_rounded = self._round_days(work_entry_type, days)
                add_days_rounding += (days - day_rounded)
                attendance_line = {
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type_id,
                    'number_of_days': day_rounded,
                    'number_of_hours': day_rounded * calendar.hours_per_day,
                    'amount': hours * paid_amount / total_hours if is_paid else 0,
                }
                res.append(attendance_line)
        return res

    def _round_days(self, work_entry_type, days):
        attendance = days
        if self.payslip_run_id:
            if self.payslip_run_id.type_payroll == 'monthly' and days != 30:
                days = days - self.date_to.day + 30
            elif self.payslip_run_id.type_payroll == 'bi-monthly' and self.date_to.day > 15:
                days = days - (self.date_to.day - 30)
            elif self.payslip_run_id.type_payroll == 'weekly' and days < 7.5 :
                days += 0.5
        if work_entry_type.round_days != 'NO':
            precision_rounding = 0.5 if work_entry_type.round_days == "HALF" else 1
            day_rounded = float_round(attendance, precision_rounding=precision_rounding, rounding_method=work_entry_type.round_days_type)
            return day_rounded
        return days

    def compute_sheet(self):
        for s in self:
            res = s._get_inputs_line(s.contract_id,s.date_from,s.date_to)
            if not s.input_line_ids and res:
                s.input_line_ids.create(res)
            else:
                for r in res:
                    cont = 0
                    for lines in s.input_line_ids:
                        if r.get('input_id') and r['input_id'] == lines.input_id.id:
                            lines.update(r)
                            cont = 1
                            break
                    if not cont:
                        s.input_line_ids.create([r])
            super(hrPayslip,s).compute_sheet()

    def action_payslip_done(self):
        for payslip in self:
            for inputs in payslip.input_line_ids:
                if inputs.input_id:
                    inputs.input_id.total_discount = inputs.amount
        super(hrPayslip,self).action_payslip_done()

class hrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    type_payroll = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly')

    @api.onchange('type_payroll','date_start')
    def onchange_type_payroll(self):
        if self.type_payroll == 'monthly':
            self.date_start = self.date_start.replace(day=1)
            self.date_end = self.date_start.replace(day=1)+relativedelta(months=1)+timedelta(days=-1)
        if self.type_payroll == 'bi-monthly':
            if self.date_start.day == 1:
                self.date_end = self.date_start.replace(day=15)
            else:
                self.date_end = self.date_start.replace(day=1)+relativedelta(months=1)+timedelta(days=-1)
        if self.type_payroll == 'weekly':
            self.date_end = self.date_start + timedelta(days=6)
            if self.date_end.month != self.date_start.month:
                self.date_end = self.date_start.replace(day=1)+relativedelta(months=1)+timedelta(days=-1)

    def print_xlsx_payroll(self):
        file_data =  BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        query_totales = """select sum(hpl.total), hpl.name, hpl."sequence" from hr_payslip_run hpr 
                                join hr_payslip hp on hp.payslip_run_id =hpr.id
                                join hr_payslip_line hpl on hpl.slip_id = hp.id
                                join hr_employee he on hp.employee_id = he.id
                                join hr_salary_rule hsr on hpl.salary_rule_id = hsr.id
                                where hsr.appears_on_payslip """
        query = """select distinct(hpl.name), hpl."sequence" from hr_payslip_run hpr 
                            join hr_payslip hp on hp.payslip_run_id =hpr.id
                            join hr_payslip_line hpl on hpl.slip_id = hp.id
                            join hr_salary_rule hsr on hpl.salary_rule_id = hsr.id
                            where hpr.id=%s and hsr.appears_on_payslip
                            order by hpl.sequence """ %(self.id)
        name = self.name
        self.xslx_body(workbook,query_totales,query,name,False)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': self.name,
            'store_fname': self.name + '.xlsx',
        })
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += "/web/content/%s?download=true" %(attachment.id)
        return{
        "type": "ir.actions.act_url",
        "url": url,
        "target": "new",
        }
    
    def xslx_body(self,workbook,query_totales,query,name,comision):
        bold = workbook.add_format({'bold':True,'border':1,'bg_color':'#067eb2'})
        bold.set_center_across()
        number = workbook.add_format({'num_format':'$#,##0.00','border':1})
        number2 = workbook.add_format({'num_format':'$#,##0.00','border':1,'bg_color':'#067eb8','bold':True})
        border = workbook.add_format({'border':1})
        condition = " and hpr.id=%s group by hpl.sequence, hpl.name" %(self.id)
        struct_id = False
        if comision:
            struct_id = self.env['res.config.settings'].sudo(1).search([], limit=1, order="id desc").struct_id
            if not struct_id:
                raise ValidationError(_('No ha registrado una estructura para comisiones en sus configuraciones.'))
            condition_2 =" and hp.struct_id=%s" %struct_id.id 
            condition = condition_2 + condition
        col = 2
        colspan = 0
        sheet = workbook.add_worksheet(name)
        sheet.write(1,4,name.upper())
        sheet.write(col,colspan,'Mes')
        sheet.write(col,colspan+1,self.date_start.month)
        sheet.write(col,colspan+2,'Periodo')
        sheet.write(col,colspan+3,self.date_start.year)
        col += 1
        sheet.write(col,colspan,'No.',bold)
        sheet.write(col,colspan+1,'Localidad',bold)
        sheet.write(col,colspan+2,'Area',bold)
        sheet.write(col,colspan+3,'Departamento',bold)
        sheet.write(col,colspan+4,'Empleado',bold)
        sheet.freeze_panes(col+1,colspan+5)
        sheet.write(col,colspan+5,'Cedula',bold)
        sheet.write(col,colspan+6,'Dias Trabajados',bold)
        sheet.write(col,colspan+7,'Sueldo',bold)
        self.env.cr.execute(query)
        inputs = self.env.cr.fetchall()
        cont = 7
        dtc = {}
        for line in inputs:
            cont+=1
            sheet.write(col,colspan+cont,line[0],bold)
            dtc['%s' %(line[0])] =colspan+cont
        address = ''
        no = 0
        col -=1
        lineas = sorted(self.slip_ids,key=lambda x: x.employee_id.work_location)
        for payslip in lineas:
            if struct_id == False or payslip.struct_id == struct_id:
                if address != payslip.employee_id.work_location:
                    col += 1
                    if address != '':
                        no = 0
                        sheet.write(col,colspan+4, 'TOTAL %s' % address,bold)
                        self.env.cr.execute(query_totales+ (" and he.work_location = '%s'" %(address)) + condition)
                        totals = self.env.cr.fetchall()
                        cont = 8
                        for total in totals:
                            while (cont < dtc[total[1]]):
                                sheet.write(col,cont,0.00,number2)
                                cont += 1
                            sheet.write(col,dtc[total[1]],abs(total[0]),number2)
                            cont += 1
                    address = payslip.employee_id.work_location
                    col += 1    
                    sheet.merge_range(col,0,col,3,address,bold)
                no += 1
                col += 1
                if payslip.contract_id.department_id.parent_id:
                    department = payslip.contract_id.department_id.parent_id.name
                else:
                    department = payslip.contract_id.department_id.name
                sheet.write(col,colspan,no,border)
                sheet.write(col,colspan+1,payslip.employee_id.work_location,border)
                sheet.write(col,colspan+2, department,border)
                sheet.write(col,colspan+3, payslip.contract_id.department_id.name,border)
                sheet.write(col,colspan+4, payslip.contract_id.employee_id.name,border)
                sheet.write(col,colspan+5, payslip.contract_id.employee_id.identification_id,border)
                for days in payslip.worked_days_line_ids:
                    if days.code == 'WORK100':
                        day = days.number_of_days
                sheet.write(col,colspan+6, day,border)
                sheet.write(col,colspan+7, payslip.contract_id.wage,number)
                cont = 8
                for lines in payslip.line_ids:
                    if lines.appears_on_payslip:
                        while (cont < dtc[lines.name]):
                            sheet.write(col,cont,0.00,number)
                            cont += 1
                        sheet.write(col,dtc[lines.name],abs(float(lines.total)),number)
                        cont += 1
                
        col+=1
        sheet.write(col,colspan+4, 'TOTAL %s' % address,bold)
        self.env.cr.execute(query_totales+ (" and he.work_location = '%s'" %(address)) + condition)
        totals = self.env.cr.fetchall()
        cont = 8
        for total in totals:
            while (cont < dtc[total[1]]):
                sheet.write(col,cont,0.00,number2)
                cont += 1
            sheet.write(col,dtc[total[1]],abs(total[0]),number2)
            cont += 1
        col += 1
        self.env.cr.execute(query_totales + condition)
        totals = self.env.cr.fetchall()
        sheet.write(col,colspan+4, 'TOTAL GENERAL',bold)
        cont = 8
        for total in totals:
            while (cont < dtc[total[1]]):
                sheet.write(col,cont,0.00,number2)
                cont += 1
            sheet.write(col,dtc[total[1]],abs(total[0]),number2)
            cont += 1
