# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

class wizardHrAttendance(models.TransientModel):
    _name = "wizard.hr.attendance"
    _description = "Wizard Asistencia"
    _rec_name = "date_from"

    date_from = fields.Date("Desde")
    date_to = fields.Date("Hasta")
    state = fields.Selection([('draft','Borrador'),('done','Realizado')], default="draft")

    def generate_issue(self):
        attendance_ids = self.env['hr.attendance'].search([('check_in','>=',self.date_from),('check_in','<=',self.date_to),('state','=','approved')],order="employee_id")
        if not attendance_ids:
            raise UserError(_("No hay asistencias aprovadas para generar novedad"))
        attendance_ids.generate_input_issue(self.date_from,self.date_to)
        self.state="done"