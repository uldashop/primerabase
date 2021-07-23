# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError

class hrEmployee(models.Model):
    _inherit = 'hr.employee'

    performance = fields.Float(string="Eval Perfomance")
    kpi = fields.Float(string="KPI's")
    assessment_center = fields.Float(string="Assessment Center")
    cognitive = fields.Float(string="Cognitive Indicator")
    emotional = fields.Float(string="Emotional Indicator")

    @api.model
    def create(self, vals):
        talent_obj = self.env['hr.talent.growth']
        line = super(hrEmployee, self).create(vals)
        talent_obj.sudo().create({'employee_id':line.id})
        return line
