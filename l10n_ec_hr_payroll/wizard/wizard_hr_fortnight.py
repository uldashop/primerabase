# -*- coding: utf-8 -*-
from odoo import _,api,fields,models
from odoo.exceptions import (
    Warning as UserError,
    ValidationError
)
from datetime import date, datetime, time, timedelta

type_doc = {
    'week': 'Semanal',
    'fortnight': 'Quincenal',
}

class WizardPayFortnight(models.TransientModel):
    _name = "wizard.hr.fortnight"

    date_from = fields.Date('Periodo desde', default=date.today().replace(day=1))
    date_to = fields.Date('Periodo hasta', default=date.today())
    name = fields.Char('name')
    sequence_id = fields.Many2one('ir.sequence', string="Secuencia")
    payment_type = fields.Selection([('week','Semanal'),('fortnight','Quincena')],'Tipo',default='fortnight')
    state = fields.Selection([
         ('init', 'Inicio'),
         ('success', 'Exito')
    ], string='Estado', default='init')
    company_id = fields.Many2one('res.company',string='Compañía', default=lambda self:self.env.company.id)
    input_ids = fields.One2many('hr.input','advance_id',string="Ingresos/Egresos")
    line_ids = fields.Char(string="lineas")

    @api.onchange('input_ids')
    def onchange_inputs(self):
        data = ''
        if self.input_ids:
            for line in self.input_ids._ids:
                if data:
                    data += ','
                data += str(line)
            self.line_ids = data

    @api.onchange('date_from')
    def onchange_period(self):
        if self.date_from:
            self.date_to = self.date_from + timedelta(days=14)

    def gen_pay(self):
        ids = self.env.context.get('active_ids', []) or [] #obtiene los ids de los objetos seleccionados
        employee_ids = self.env['hr.employee'].browse(ids) #arreglo que trae los ids seleccionados 
        pay_obj = self.env['hr.fortnight'] #refrencia tabla de pagos quincenales donde se va a grabar
        journal_pay = self.validate_journal()
        if not journal_pay:
            raise ValidationError(_("Debe configurar un diario de pago de quincena en Configuraciones."))
        lines=[]
        data = []
        if self.line_ids:
            line_ids = self.line_ids.split(',')
            for values in line_ids:
                data.append(int(values))
        input_ids = self.env['hr.input'].browse(data)

        for e in employee_ids:
            amount = 0
            for inputs in input_ids:
                for line in inputs.line_ids:
                    if line.employee_id == e:
                        if inputs.input_type_id.type == 'income':
                            amount += (line.amount * inputs.percent /100)
                        else:
                            amount -= (line.amount * inputs.percent /100)
                        line.total_discount += (line.amount * inputs.percent /100)
                        lines = self.generate_account_move_line(e, line, inputs, lines, 0)
            salary = e.percent_wage * e.contract_id.wage / 100
            if salary:
                lines = self.generate_account_move_line(e, False, False, lines, salary)
            amount += (e.percent_wage * e.contract_id.wage / 100)
            if amount < 0:
                raise ValidationError(_("El empleado %s genera valores en negativo."))
            if amount:
                payment = self.payment_generate(e,amount)
                pay_obj.sudo().create(payment)
                self.create_payment(e, amount,journal_pay)

        self.create_account_move(lines)
        self.state='success'

        return {
             'type': 'ir.actions.act_window',
             'res_model': 'wizard.hr.fortnight',
             'view_mode': ' form',
             'view_type': ' form',
             'res_id': self.id,
             'views': [(False, 'form')],
             'target': 'new',
         }

    def create_account_move(self, lines):
        pass

    def generate_account_move_line(self,employee, line, inputs, lines, amount):
        return lines

    def create_payment(self, employee, amount, journal_pay):
        pass

    def validate_journal(self):
        return True
    
    def payment_generate(self, employee, amount):
        return {
            'employee_id': employee.id,
            'amount': amount,
            'date_from':self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'name': 'Pago %s correspondiente al periodo desde %s hasta %s' % (type_doc[self.payment_type],str(self.date_from), str(self.date_to)),
            }