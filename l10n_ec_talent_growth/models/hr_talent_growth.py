# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError

class hrTalentGrowth(models.Model):
    _name = "hr.talent.growth"
    _description = "Talent Growth"
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    performance = fields.Float(string="Eval Perfomance", related="employee_id.performance", store=True)
    kpi = fields.Float(string="KPI's", related="employee_id.kpi", store=True)
    assessment_center = fields.Float(string="Assessment Center", related="employee_id.assessment_center", store=True)
    cognitive = fields.Float(string="Cognitive Indicator", related="employee_id.cognitive", store=True)
    emotional = fields.Float(string="Emotional Indicator", related="employee_id.emotional", store=True)
    total =  fields.Float(string="Total", compute="total_eval")
    active = fields.Boolean('Active', related='employee_id.active')

    def total_eval(self):
        for s in self:
            s.total = (s.assessment_center + s.performance + s.kpi + s.cognitive + s.emotional)/5

    # def _compute_employee(self):
    #     if self.employee_id:
    #         self.performance = self.employee_id.performance
    #         self.kpi = self.employee_id.kpi
    #         self.assessment_center = self.employee_id.assessment_center
    #         self.cognitive = self.employee_id.cognitive
    #         self.emotional = self.employee_id.emotional