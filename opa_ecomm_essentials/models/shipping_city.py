# -*- coding: utf-8 -*-

from odoo import models, fields, api

class shipping_city(models.Model):
    _name = "shipping.city"

    name = fields.Char("Nombre")
    state_id = fields.Many2one('res.country.state', 'Provincia')


class resCountryState(models.Model):
    _inherit = 'res.country.state'
    _order = 'name'

    city_ids = fields.One2many('shipping.city','state_id', string="Ciudades")

    def get_website_sale_city(self, mode='billing'):
        res = self.sudo().city_ids
        return res
