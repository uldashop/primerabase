# -*- coding: utf-8 -*-
from odoo import _, api, models, fields
from datetime import date

class hrIncomeTax(models.Model):
    _name = "hr.income.tax"
    _description = "Income Tax"
    _rec_name = "code"

    code = fields.Char("Code")
    fiscal_year = fields.Char(string="Fiscal Year", default=date.today().year)
    amount = fields.Float("Basic Fraction")
    amount_to = fields.Float("Excess Until")
    tax_amount = fields.Float("Basic Fraction Tax")
    excess_tax_amount = fields.Float("Percent Excess Tax Fraction")