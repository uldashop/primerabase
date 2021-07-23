# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from datetime import date

class slideChannel(models.Model):
    _inherit = 'slide.channel'

    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date") 

    @api.model
    def archive_course(self):
        for s in self:
            if s.date_end and s.date_end < date.today() and s.active:
                s.active = False
            if s.date_end and s.date_end >= date.today() and not s.active:
                s.active = True


