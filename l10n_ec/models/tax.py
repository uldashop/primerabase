# -*- coding: utf-8 -*-
 
import time

from odoo import api, fields, models, _
import time, datetime, calendar

class tax_group(models.Model):
    _inherit = "account.tax.group"
    _name = "account.tax.group"

    code = fields.Char("Codigo")


class AccountReportTax(models.TransientModel):
    _name = 'account.report.tax'

    @api.model
    def _default_start(self):
        today = datetime.date.today()
        today = today.replace(day=1)
        res = fields.Date.to_string(today)
        return res

    @api.model
    def _default_end(self):
        today = datetime.date.today()
        first, last = calendar.monthrange(today.year, today.month)
        today = today.replace(day=last)
        res = fields.Date.to_string(today)
        return res

    date_start = fields.Date('Inicio Periodo', default=_default_start)
    date_end = fields.Date('Final de Periodo', default=_default_end)
    report_type = fields.Selection([
        ('104', '104'),
        ('103', '103')
    ], string="Tipo de reporte", default="104")

    def action_print(self):
        return self.env.ref('l10n_ec.account_tax_report').report_action(self)
        