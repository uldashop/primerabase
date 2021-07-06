# -*- coding: utf-8 -*-
from odoo import _,api,fields,models
from datetime import date

class PayFortnight(models.Model):
    _inherit = "hr.fortnight"

    journal_id = fields.Many2one('account.journal', string="Diario")