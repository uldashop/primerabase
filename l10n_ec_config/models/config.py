# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    # _name = 'partner.config'

    module_l10n_ec_config = fields.Boolean()
    default_partner_id = fields.Many2one(
        'res.partner', default_model='account.move')
    amount_total = fields.Float()

    @api.model
    def get_values(self):
        res = super(AccountConfigSettings, self).get_values()
        ICPSudo = self.env['ir.default'].sudo()
        res.update(
            amount_total=ICPSudo.get(
                "res.config.settings", 'amount_total', False, self.env.company.id
            ),
        )
        return res

    def set_values(self):
        super(AccountConfigSettings, self).set_values()
        ICPSudo = self.env['ir.default'].sudo()
        ICPSudo.set(
            "res.config.settings", 'amount_total',
            self.amount_total, False, self.env.company.id
        )


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        if self.type == 'out_invoice':
            default = self.env['ir.default'].sudo()
            max_amount = default.get(
                'res.config.settings', 'amount_total'
            )
            partner_id = default.get(
                'account.move', 'partner_id'
            )
            if self.partner_id.id == partner_id and self.amount_total > max_amount:
                raise UserError(_(
                    "Sale for %s can't be over $%.2f" % (
                        self.partner_id.name, max_amount
                    )
                ))
        return super(AccountMove, self).action_post()

    @api.model
    def default_get(self, default_fields):
        values = super(AccountMove, self).default_get(default_fields)
        if self._context.get('default_type') != 'out_invoice':
            values.get('partner_id') == self.env['ir.default'].sudo().get(
                'account.move', 'partner_id'
            ) and values.update({
                'partner_id': False
            })
        return values


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        default = self.env['ir.default'].sudo()
        max_amount = default.get(
            'res.config.settings', 'amount_total'
        )
        partner_id = default.get(
            'account.move', 'partner_id'
        )
        if self.partner_id.id == partner_id and self.amount_total > max_amount:
            raise UserError(_(
                "Sale for %s can't be over $%.2f" % (
                    self.partner_id.name, max_amount
                )
            ))
        return super(SaleOrder, self).action_confirm()
