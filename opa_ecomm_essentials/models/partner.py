# -*- coding: utf-8 -*-
from odoo import models, fields, api

class resPartner(models.Model):
    _inherit = 'res.partner'

    city_id = fields.Many2one('shipping.city', string="Ciudad de Envio")

    @api.constrains('city_id')
    def constrains_city_id(self):
        if self.city_id:
            self.city = self.city_id.name