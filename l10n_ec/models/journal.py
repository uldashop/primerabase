# -*- coding: utf-8 -*-
 

import time
from datetime import datetime, date

from odoo import api, fields, models
from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    auth_out_invoice_id = fields.Many2one(
        'account.authorisation',
        'Secuencia Facturas'
    )
    auth_out_refund_id = fields.Many2one(
        'account.authorisation',
        'Secuencia Notas de Credito'
    )
    auth_retention_id = fields.Many2one(
        'account.authorisation',
        'Para Retenciones'
    )
    auth_out_debit_id = fields.Many2one(
        'account.authorisation',
        'Para Notas de debito'
    )
    # auth_in_debit_id = fields.Many2one(
    #     'account.authorisation',
    #     'Para Notas de debito'
    # )
    auth_out_liq_purchase_id = fields.Many2one(
        'account.authorisation',
        'Para Liquidacion de compras'
    )

    format_transfer_id = fields.Selection([
        ('banco_pichincha','Banco Pichincha'),
        ('banco_austro','Bando del Austro'),
        ('banco_internacional','Banco Internacional'),
        ('banco_pacifico','Banco del Pacifico'),
        ('banco_bolivariano','Banco Bolivariano')],string='Formato de Transferencia Bancaria')
