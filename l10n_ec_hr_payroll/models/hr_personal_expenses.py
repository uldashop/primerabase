# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError

class hrPersonalExpenses(models.Model):
    _name = "hr.personal.expenses"
    _description = _("Personal Expenses")
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(string="Employee", comodel_name='hr.employee')
    date = fields.Date('Date', default=date.today())
    fiscal_year = fields.Char('Fiscal Year')
    day = fields.Char('Day', compute="_get_dates")
    city = fields.Char('City')
    identification_id = fields.Char('ID')
    # name = fields.Char('Apellidos y Nombres')
    company_id = fields.Many2one(string="Company", comodel_name='res.company')

    incomes = fields.Float('(+) TOTAL INCOMES WITH THIS EMPLOYER (with the employer that receives the most income)')
    other_income = fields.Float('(+) TOTAL INCOMES WITH OTHER EMPLOYERS (If these exist)')
    projected_income = fields.Float('(=) TOTAL PROJECTED INCOMES', compute="_get_totals")

    housing_expense = fields.Float('(+) HOUSING EXPENSES') 
    education_expense = fields.Float('(+) EXPENSES OF EDUCATION, ART AND CULTURE')
    health_expense = fields.Float('(+) HEALTH EXPENSES')
    clothing_expense = fields.Float('(+) CLOTHING EXPENSES')
    food_expense = fields.Float('(+) FOOD EXPENSES')
    projected_expense = fields.Float('(=) TOTAL PROJECTED EXPENSES', compute="_get_totals")
    tax_pay = fields.Float('INCOME TAX VALUE', compute="_get_tax")

    def exceeds_expenses(self):
        raise ValidationError(_("Exceeds personal spending limit"))

    @api.constrains('housing_expense','education_expense','health_expense','clothing_expense','food_expense','fiscal_year')
    def constrains_project_expense(self):
        limit_id = self.env['hr.personal.expenses.limit'].search([('name','=',self.fiscal_year)])
        if limit_id:
            if self.employee_id.galapagos_beneficiary:
                if self.projected_expense > limit_id.projected_expense_extra and not self.employee_id.catastrophic_disease:
                    self.exceeds_expenses()
                elif self.projected_expense > limit_id.catastrophic_diseases_extra and self.employee_id.catastrophic_disease:
                    self.exceeds_expenses()
            else:
                if self.projected_expense > limit_id.projected_expense and not self.employee_id.catastrophic_disease:
                    self.exceeds_expenses()
                elif self.projected_expense > limit_id.catastrophic_diseases and self.employee_id.catastrophic_disease:
                    self.exceeds_expenses()

    @api.onchange('housing_expense','education_expense','health_expense','clothing_expense','food_expense','fiscal_year')
    def onchange_limit_expenses(self):
        limit_id = self.env['hr.personal.expenses.limit'].search([('name','=',self.fiscal_year)])
        if limit_id:
            if self.employee_id.galapagos_beneficiary:
                if self.food_expense > limit_id.food_expense_extra:
                    self.food_expense = limit_id.food_expense_extra
                elif self.housing_expense > limit_id.housing_expense_extra:
                    self.housing_expense = limit_id.housing_expense_extra
                elif self.clothing_expense > limit_id.clothing_expense_extra:
                    self.clothing_expense = limit_id.clothing_expense_extra
                elif self.education_expense > limit_id.education_expense_extra:
                    self.education_expense = limit_id.education_expense_extra
                elif self.health_expense > limit_id.health_expense_extra and not self.employee_id.catastrophic_disease:
                    self.health_expense = limit_id.health_expense_extra
                elif self.health_expense > limit_id.catastrophic_diseases_extra and self.employee_id.catastrophic_disease:
                    self.health_expense = limit_id.catastrophic_diseases_extra
            else:
                if self.food_expense > limit_id.food_expense:
                    self.food_expense = limit_id.food_expense
                elif self.housing_expense > limit_id.housing_expense:
                    self.housing_expense = limit_id.housing_expense
                elif self.clothing_expense > limit_id.clothing_expense:
                    self.clothing_expense = limit_id.clothing_expense
                elif self.education_expense > limit_id.education_expense:
                    self.education_expense = limit_id.education_expense
                elif self.health_expense > limit_id.health_expense and not self.employee_id.catastrophic_disease:
                    self.health_expense = limit_id.health_expense
                elif self.health_expense > limit_id.catastrophic_diseases and self.employee_id.catastrophic_disease:
                    self.health_expense = limit_id.catastrophic_diseases
        else:
            raise UserError(_('First do you define a limit for personal expenses of %s' %(self.fiscal_year)))
    
    # Funcion para calcular los totales
    @api.depends('incomes','other_income','housing_expense','education_expense',
                 'health_expense','clothing_expense','food_expense')
    def _get_totals(self):
        for s in self:
            s.projected_income = s.incomes + s.other_income
            s.projected_expense = s.housing_expense + s.education_expense + s.health_expense + s.clothing_expense + s.food_expense
        

    # Funcion para cargar los campos de fecha formateado
    @api.depends('date')
    def _get_dates(self):
        for s in self:
            s.fiscal_year = '{0:%Y}'.format(s.date)
            s.day = '{0:%d}'.format(s.date)

    def _get_tax(self):
        for s in self:
            contract_id = s.env['hr.contract'].search([('employee_id','=',s.employee_id.id),('state','=','open')])
            if contract_id:
                limit = s.env['hr.income.tax'].search([('amount', '<=', contract_id.wage *12),('amount_to', '>=', contract_id.wage*12),('fiscal_year','=',s.fiscal_year)])
                s.tax_pay = (limit.excess_tax_amount * contract_id.wage / 100) if limit else 0
            else:
                s.tax_pay = 0

class hrPersonalExpensesLimit(models.Model):
    _name = "hr.personal.expenses.limit"
    _description = "Limit of Personal Expenses"

    name = fields.Char("FISCAL YEAR", default= date.today().year)
    housing_expense = fields.Float('HOUSING EXPENSES') 
    education_expense = fields.Float('EXPENSES OF EDUCATION, ART AND CULTURE')
    health_expense = fields.Float('HEALTH EXPENSES')
    clothing_expense = fields.Float('CLOTHING EXPENSES')
    food_expense = fields.Float('FOOD EXPENSES')
    projected_expense = fields.Float('TOTAL EXPENSES')
    catastrophic_diseases = fields.Float('CATASTROPHIC DISEASES')
    housing_expense_extra = fields.Float('HOUSING EXPENSES') 
    education_expense_extra = fields.Float('EXPENSES OF EDUCATION, ART AND CULTURE')
    health_expense_extra = fields.Float('HEALTH EXPENSES')
    clothing_expense_extra = fields.Float('CLOTHING EXPENSES')
    food_expense_extra = fields.Float('FOOD EXPENSES')
    projected_expense_extra = fields.Float('TOTAL EXPENSES')
    catastrophic_diseases_extra = fields.Float('CATASTROPHIC DISEASES')

    _sql_constraints = [
        (
            'unique_personal_expenses_limit', 'UNIQUE(name)',
            _('Personal spending limit one per year'))
    ]