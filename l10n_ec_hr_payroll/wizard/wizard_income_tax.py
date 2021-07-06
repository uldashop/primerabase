# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import Warning as UserError, ValidationError
from datetime import date, datetime, time

class WizardImpuestoRenta(models.TransientModel):
    _name = "hr.wizard.income.tax"

    name = fields.Many2one(string="Empleado", comodel_name='hr.employee')
    date = fields.Date('Fecha Entrega', default=date.today())
    year= fields.Char('Ejercicio Fiscal')

    util = fields.Float('PARTICIPACIÓN UTILIDADES (305)')
    ing_grav_otroempl = fields.Float('INGRESOS GRAV.CON OTROS EMPLEADORES (307)')
    otros_ing = fields.Float('OTROS ING. QUE NO CONSTITUYEN RENTA GRAVADA (317)')
    apor_iess = fields.Float('APOR. IESS OTROS EMPLEADORES (353)')
    imp_ret_asum = fields.Float('IMP. RET. Y ASUM. x OTROS EMPLEADORES (403)')
    exo_discapacidad = fields.Float('(-) EXONERACIÓN POR DISCAPACIDAD (371)')
    exo_ter_edad = fields.Float('(-) EXONERACIÓN POR TERCERA EDAD (373)')
    imp_asum_estempl = fields.Float('IMP. A LA RENTA ASUMIDO POR ESTE EMPLEADOR (381-405)')

    def print_107(self):
        return self.env.ref('l10n_ec_hr_payroll.report_income_tax').report_action(self)

    def calcule_sayings(self, salaryrulecode):
        if not isinstance(salaryrulecode, list):
            salaryrulecode = [salaryrulecode]
        obj_payslip = self.env['hr.payslip']
        value = 0.00
        date_init = str(self.year) + '-01-01'
        date_end = str(self.year) + '-12-31'
        payslip_ids = obj_payslip.search([('employee_id','=',self.name.id),
                                        ('date_from','>=',date_init),
                                        ('date_to','<=',date_end),
                                        ('state','=','paid')])
        for payslip in payslip_ids:
            for lines in payslip.line_ids:
                if lines.code in salaryrulecode or lines.code in salaryrulecode[0].upper():
                    value += lines.total
        if value < 0:
            value = value * -1
        return value

    def calcule_personal_expenses(self):
        obj_expenses = self.env['hr.personal.expenses']
        expense_id = obj_expenses.search([('employee_id','=',self.name.id),
                                        ('fiscal_year','>=',self.year)], limit=1)
        if expense_id:
            result = {
            'housing': expense_id.housing_expense,
            'health': expense_id.health_expense,
            'education': expense_id.education_expense,
            'food': expense_id.food_expense,
            'clothing': expense_id.clothing_expense
        }
        else:
            result = {
                'housing': 0.00,
                'health': 0.00,
                'education': 0.00,
                'food': 0.00,
                'clothing': 0.00
            }
        return result

    def tax_code(self):
        expenses = self.calcule_personal_expenses()
        val301 = self.calcule_sayings(['SALARIO'])
        val303 = self.calcule_sayings(['COMISION','BONIF','HEXTRA','HSUPL','MOVIL'])
        val305 = self.util
        val307 = self.ing_grav_otroempl
        val311 = self.calcule_sayings(['ProvDec13'])
        val313 = self.calcule_sayings(['ProvDec14'])
        val315 = self.calcule_sayings(['PROVFR']) 
        val317 = self.otros_ing
        val351 = self.calcule_sayings('ApIESSPer')
        val353 = self.apor_iess
        val361 = expenses['housing']
        val363 = expenses['health']
        val365 = expenses['education']
        val367 = expenses['food']
        val369 = expenses['clothing']
        val371 = self.exo_discapacidad
        val373 = self.exo_ter_edad
        val381_405 = self.imp_asum_estempl
        val401 = self.check_tax((val301+val303)-(val361+val363+val365+val367+val369+val351))
        val403 = self.imp_ret_asum
        val407 = self.calcule_sayings('IMPRENT')
        result = {
            '301': val301,
            '303': val303,
            '305': val305,
            '307': val307,
            '311': val311,
            '313': val313,
            '315': val315,
            '317': val317,
            '351': val351,
            '353': val353,
            '361': val361,
            '363': val363,
            '365': val365,
            '367': val367,
            '369': val369,
            '371': val371,
            '373': val373,
            '381-405': val381_405,
            '399': val303+val301+val305+val307-val351-val353-val361-val363-val365-val367-val369-val371-val373+val381_405,
            '401': val401,
            '403': val403,
            '407': val407,
            '349': val303+val301+val305+val381_405
        }
        for k,v in result.items():
            result[k] = '{:.2f}'.format(v)
        return result


    def check_tax(self, value):
        obj_income_id = self.env['hr.income.tax']
        income_id = obj_income_id.search([('amount','<=',value),('amount_to','>=',value)])
        amount = value - income_id.amount
        amount = (amount * (income_id.excess_tax_amount / 100)) + income_id.tax_amount
        return amount