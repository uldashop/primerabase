# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import ValidationError, UserError
import pytz

day_of_week = {
    'Monday':'0',
    'Tuesday':'1',
    'Wednesday':'2',
    'Thursday':'3',
    'Friday':'4',
    'Saturday':'5',
    'Sunday':'6',
}

class hrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'

    input_hour = fields.Char(string="Hora de Entrada")
    output_hour  = fields.Char(string="Hora de Salida")
    date = fields.Char(string="Fecha")
    barcode = fields.Char(string="Codigo")
    state = fields.Selection([('draft','Borrador'),
                              ('approved','Aprovado'),
                              ('rejected','Rechazado'),
                              ('send','Enviado')],string="Estado", default="draft")
    delay = fields.Char(string="Atrasos", help="Este campo es solo informativo")
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True, store=True)

    # Function is to add employee search, by barcode field
    @api.model
    def create(self, vals):
        cont = False
        for x in vals:
            if x == 'barcode':
                cont = True
                break;
        if not cont:
            vals['barcode'] = ''
        if vals['barcode']:
            employee = self.env['hr.employee'].search([('barcode','=',vals['barcode'])], limit=1)
            vals['employee_id'] = employee.id
        return super(hrAttendance, self).create(vals)


    #Validation to not delete assistance where status not equal to draft
    def unlink(self):
        for s in self:
            if s.state != 'draft':
                raise ValidationError(_("No se puede eliminar un registro que no esta en estado borrador."))
        super(hrAttendance,self).unlink()


    def button_approved(self):
        for s in self:
            if s.state == 'draft':
                s.state = 'approved'

    #Update Inputs to payslip of employee if exists
    def update_lines(self,employee_id,amount,obj_id,input_obj):
        exist = False
        for line in input_obj:
            if employee_id == line.employee_id.id:
                exist = True 
                line.amount += amount
                break
        if not exist:
            input_obj.create({
                            'employee_id':employee_id,
                            'amount': '%.2f' % amount,
                            'date': input_obj[0].date,
                            'input_type_id': input_obj[0].input_type_id.id,
                            # 'percent': 100,
                            })
        self.env.cr.commit()
       
    #Create inputs to payslip of employee
    def generate_input_issue(self,date_from,date_to):
        input_obj = self.env['hr.input']
        input_id = self.env['hr.payslip.input.type'].search([('code','=','HEXT')],limit=1)
        supl_id = self.env['hr.payslip.input.type'].search([('code','=','HSUP')],limit=1)
        obj_id = input_obj.search([('date','>=',date_from),('date','<=',date_to),('input_type_id','=',input_id.id)])
        obj_supl_id = input_obj.search([('date','>=',date_from),('date','<=',date_to),('input_type_id','=',supl_id.id)])
        lines = []
        lines_supl = []
        error =[]
        hour_after = self.env['ir.default'].sudo().get("res.config.settings",'hours_after_attendance',False,self.env.company.id)
        approved_hour = self.env['ir.default'].sudo().get("res.config.settings",'approved_hour',False,self.env.company.id)
        employee_id = None
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        res = self.sorted(lambda x:x.employee_id)
        for s in res:
            s.state = 'send'
            if not employee_id:
                employee_id = s.employee_id
                amount = 0.00
                supl = 0.00
            
            if employee_id != s.employee_id:
                if amount:
                    if obj_id:
                        self.update_lines(employee_id.id,amount,input_obj,obj_id)
                    else:
                        lines.append({
                            'employee_id':employee_id.id,
                            'amount': '%.2f' % amount,
                            'date': date_to,
                            'input_type_id': input_id.id,
                            # 'percent': 100,
                        })
                if supl:
                    if obj_supl_id:
                        self.update_lines(employee_id.id,supl,input_obj,obj_supl_id)
                    else:
                        lines_supl.append({
                            'employee_id':employee_id.id,
                            'amount': '%.2f' % supl,
                            'date': date_to,
                            'input_type_id': supl_id.id,
                            # 'percent': 100,
                        })
                amount = 0.00
                supl = 0.00 
                employee_id = s.employee_id

            if s.employee_id.extra_hour:
                contract_id = self.env['hr.contract'].search([('employee_id','=',s.employee_id.id),('state','=','open')])
                if contract_id:
                    salary = contract_id.wage / contract_id.resource_calendar_id.hours_per_day / 30
                    check_in = str(pytz.utc.localize(s.check_in).astimezone(tz).strftime('%H:%M:%S'))
                    check_out = str(pytz.utc.localize(s.check_out).astimezone(tz).strftime('%H:%M:%S'))
                    date_out = str(pytz.utc.localize(s.check_out).astimezone(tz).strftime('%d/%m/%Y'))
                    check_out_real = datetime.strptime("%s %s" %(date_out ,check_out),"%d/%m/%Y %H:%M:%S")
                    date = str(s.check_in.strftime('%d/%m/%Y'))
                    day = day_of_week[s.check_in.strftime('%A')]
                    hour_out = ''
                    leave = False
                    for leave_id in contract_id.resource_calendar_id.global_leave_ids:
                        leave_from = pytz.utc.localize(leave_id.date_from).astimezone(tz).strftime('%d/%m/%Y')
                        leave_to = pytz.utc.localize(leave_id.date_to).astimezone(tz).strftime('%d/%m/%Y')
                        if date >= leave_from and date <= leave_to:
                            leave = True
                            break
                    if day not in ('5','6') and not leave :
                        for attendance in contract_id.resource_calendar_id.attendance_ids:
                            if attendance.dayofweek == day and attendance.day_period == 'morning':
                                hour_in = str('%.2f' % attendance.hour_from).replace('.',':') + ':00'
                                if not hour_out:
                                    hour_out = str('%.2f' % (attendance.hour_to)).replace('.',':') + ':00'
                            if attendance.dayofweek == day and attendance.day_period == 'afternoon':
                                hour_out = str('%.2f' % (attendance.hour_to)).replace('.',':') + ':00'
                        
                        # horas al 50 despues de jornada laboral
                        hours_real = check_out.split(':')
                        hour_float = int(hours_real[0]) + (int(hours_real[1])*0.006)
                        if not approved_hour:
                            hours_base = hour_out.split(':')
                            hour_after = (int(hours_base[0],10)+(int(hours_base[1],10)/60))
                        if check_out_real > datetime.strptime("%s %s" %(date ,hour_out),"%d/%m/%Y %H:%M:%S" ) and hour_float >= hour_after:
                            base = ((int(hours_real[0],10)+(int(hours_real[1],10)/60))-(hour_after))
                            if base > 4:
                                base = 4
                            elif base < 0:
                                base = 0
                            amount += (base * salary *1.5)
                    else:
                        hours_base = check_in.split(':')
                        hours_real = check_out.split(':')
                        supl += ((int(hours_real[0])+(int(hours_real[1],10)/60))-(int(hours_base[0],10)+(int(hours_base[1],10)/60))) * salary * 2

        if amount and not obj_id:
            lines.append({
                'employee_id':employee_id.id,
                'amount': '%.2f' % amount,
                'date': date_to,
                'input_type_id': input_id.id,
                # 'percent': 100,
            })
        elif amount and obj_id:
            self.update_lines(employee_id.id,amount,input_obj,obj_id)
        
        if supl and not obj_supl_id:
            lines_supl.append({
                'employee_id':employee_id.id,
                'amount': '%.2f' % supl,
                'date': date_to,
                'input_type_id': supl_id.id,
                # 'percent': 100,
            })
        elif supl and obj_supl_id:
            self.update_lines(employee_id.id,supl,input_obj,obj_supl_id)
        if lines and not obj_id:
            for l in lines:
                input_obj.create(l)
        if lines_supl and not obj_supl_id:
            for ls in lines_supl:
                input_obj.create(ls)



    @api.constrains('input_hour','output_hour','date')
    def constrains_check_in_out(self):
        # if self.date:
        #     self.date = self.date.strftime('%d/%m/%Y')

        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        if self.date and self.input_hour:
            if len(self.input_hour)> 5:
                check_in = str(tz.localize(datetime.strptime("%s %s" %(self.date,self.input_hour),'%d/%m/%Y %H:%M:%S')).astimezone(pytz.utc).strftime('%d/%m/%Y %H:%M:%S'))
                self.check_in = datetime.strptime(check_in,'%d/%m/%Y %H:%M:%S')
            else:
                check_in = str(tz.localize(datetime.strptime("%s %s:00" %(self.date,self.input_hour),'%d/%m/%Y %H:%M:%S')).astimezone(pytz.utc).strftime('%d/%m/%Y %H:%M:%S'))
                self.check_in = datetime.strptime(check_in,'%d/%m/%Y %H:%M:%S')
        if self.date and self.output_hour:
            if len(self.output_hour)> 5:
                check_out = str(tz.localize(datetime.strptime("%s %s" %(self.date,self.output_hour),'%d/%m/%Y %H:%M:%S')).astimezone(pytz.utc).strftime('%d/%m/%Y %H:%M:%S'))
                self.check_out = datetime.strptime(check_out,'%d/%m/%Y %H:%M:%S')
            else:
                check_out = str(tz.localize(datetime.strptime("%s %s:00" %(self.date,self.output_hour),'%d/%m/%Y %H:%M:%S')).astimezone(pytz.utc).strftime('%d/%m/%Y %H:%M:%S'))
                self.check_out = datetime.strptime(check_out,'%d/%m/%Y %H:%M:%S')