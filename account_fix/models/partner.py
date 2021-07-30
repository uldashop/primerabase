from odoo import api, fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    test_field = fields.Char(
        string='Test field',
        required=False
    )
