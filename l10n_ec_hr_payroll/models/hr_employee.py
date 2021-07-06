# -*- coding: utf-8 -*-
from odoo import api,fields,models, _
from datetime import date
from math import ceil
from odoo.exceptions import ValidationError, UserError

class hrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    # dummy = fields.Float("Valor calculado", compute="_get_dummy")
    mensualize_13 = fields.Boolean('Mensualize 13TH', default = False)
    mensualize_14 = fields.Boolean('Mensualize 14TH', default = False)
    mensualize_fr = fields.Boolean('Mensualize Reserve Funds', default = False)
    disable = fields.Boolean('Have a Disability', default = False)
    percent_disable = fields.Float('Percent Disability')
    union_director = fields.Boolean('Union Director', default = False)
    extra_hour = fields.Boolean('Extra Hours', default = False)
    supl_hour = fields.Boolean('Suplementary Hours', default = False) 
    forthnight = fields.Boolean('Forthnight', default = False)
    percent_wage = fields.Float('Percent Wage')
    time_services = fields.Float("Years of Services", compute="_get_anios")
    rent_tax = fields.Float('Rent Tax')
    galapagos_beneficiary =  fields.Boolean('Beneficiary Galapagos', default=False)
    catastrophic_disease = fields.Boolean('Catastrophic Disease', default=False)
    apply_agreement = fields.Boolean('Apply Agreement', default=False)
    partner_id = fields.Many2one('res.partner','Substitute Employee')
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', default='monthly')

    @api.depends('contract_id')
    def _get_anios(self):
        obj_contract = self.env['hr.contract']
        service = 0
        contract_ids = obj_contract.search([('employee_id','=',self.id),('state','not in',['draft','cancel'])],order='id asc')  
        for contract in contract_ids:
            date_end = contract.date_end or date.today()
            dif = date_end - contract.date_start
            service += ceil(dif.days/365.2425)
        self.time_services = service

    def has_13months(self, date_init, contract=False):
        days = sum([(c.date_end - c.date_start).days for c in self.contract_ids if c.state == 'close'])
        days = 0 if not days else days[0]
        if not contract:
            raise ValidationError("%s debe tener un contracto activo." %(self.name))
        days += (date_init - contract.date_start).days
        if days >= 395:
            return days
        elif days < 395 and days > 366:
            return days - 366
        return 0

    def has_payment(self,date_to):
        obj_fortnight = self.env['hr.fortnight']
        pay = obj_fortnight.search([('date_from','<=',date_to),('date_to','>=',date_to),('employee_id','=',self.id),('company_id','=',self.company_id.id)])
        if pay:
            return True
        return False

    def has_payment_amount(self,date_from, date_to):
        obj_payfortnight = self.env['hr.fortnight']
        pay = obj_payfortnight.search([('date_from','>=',date_from),('date_to','<=',date_to),('employee_id','=',self.id),('company_id','=',self.company_id.id)])
        if pay:
            return sum([line.amount for line in pay])
        return 0