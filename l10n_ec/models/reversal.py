from odoo import api, fields, models, _


class account_move_reversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        res = super(account_move_reversal, self).reverse_moves()
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        for move in moves:
            if move.partner_id:
                auth = [auth.id for auth in move.partner_id.authorisation_ids if auth.type_id.code == '04']
                res['context'] = {'auth_ids': tuple(auth)}
                return res