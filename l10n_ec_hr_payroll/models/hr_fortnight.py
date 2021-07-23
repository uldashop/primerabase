# -*- coding: utf-8 -*-
from odoo import _,api,fields,models
from datetime import date

class PayFortnight(models.Model):
    _name = "hr.fortnight"
    _description = _("Fortnight")

    name= fields.Char('Nombre')
    employee_id = fields.Many2one('hr.employee', string="Empleado")
    amount = fields.Float('Monto')
    date = fields.Date('Fecha Pago', default=date.today())
    date_from = fields.Date('Periodo desde')
    date_to = fields.Date('Periodo hasta')
    company_id = fields.Many2one('res.company',string='Compañía', default=lambda self:self.env.company.id)