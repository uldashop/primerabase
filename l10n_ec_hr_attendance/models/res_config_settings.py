# -*- coding: utf-8 -*-

from odoo import api,fields, models, _
from ast import literal_eval
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hours_after_attendance = fields.Float(string='Horas Extras')
    approved_hour = fields.Boolean(string="Calcular desde hora Ingresada", default=False,
        help="""Si selecciona esta opcion las horas extras se pagaran desde la hora configurada,
        en caso contrario se contabilizaran desde la hora de salida del empleado.""")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.default'].sudo()
        hours_after_attendance = ICPSudo.get("res.config.settings",'hours_after_attendance',False,self.env.company.id)
        approved_hour = ICPSudo.get("res.config.settings",'approved_hour',False,self.env.company.id)
        res.update(hours_after_attendance=hours_after_attendance,
                   approved_hour=approved_hour,)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.default'].sudo()
        ICPSudo.set("res.config.settings",'hours_after_attendance',self.hours_after_attendance,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'approved_hour',self.approved_hour,False,self.env.company.id)
