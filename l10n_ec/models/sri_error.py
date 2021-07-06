# -*- coding: utf-8 -*-


from odoo import api, models, fields
from odoo.exceptions import Warning as UserError

class SriError(models.Model):

    _name="sri.error" #sri_error

    invoice_id = fields.Many2one('account.move', string="Factura")
    retencion_id = fields.Many2one('account.retention', string="Retencion")
    message = fields.Char('Mensaje')
    state = fields.Char('Estado')