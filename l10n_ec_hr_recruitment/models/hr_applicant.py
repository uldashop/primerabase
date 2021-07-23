# -*- coding: utf-8 -*-

from odoo import api, fields, models ,_
from odoo.exceptions import ValidationError, UserError

class hrApplicant(models.Model):
    _inherit = 'hr.applicant'

    partner_experience = fields.Char(string="Work Experience")
    partner_further = fields.Char(string="Further Training")
    partner_study = fields.Many2one('hr.study',string="Academic Preparation", domain="[('type_study','=','study')]")

    def website_form_input_filter(self, request, values):
        if 'partner_name' in values:
            values.setdefault('name', '%s\'s Application' % values['partner_name'])
        if 'salary_expected' in values:
            values['salary_expected'] = values.get('salary_expected')
        return values