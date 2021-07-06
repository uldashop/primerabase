# -*- coding:  utf-8 -*-

from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError
import base64
from itertools import groupby
from odoo.addons.account.models import account_payment as ap
import io
import os
import logging
from jinja2 import Environment, FileSystemLoader

type_account = {
    'ahorros': 'AHO',
    'corriente': 'CTE',
}

type_ident = {
    'cedula': 'C',
    'ruc': 'R',
    'pasaporte':'P',
}

ap.MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
    'liq_purchase': 1, 
    'sale_note': 1,
    'in_debit': 1,
    'out_invoice': -1,

}

ap.MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'liq_purchase': 'supplier', 
    'sale_note': 'supplier',
    'in_debit': 'supplier',
    'out_debit': 'customer',
}

class accountPayment(models.Model):
    _inherit = 'account.payment'

    account_debit_id = fields.Many2one('account.account', string="Debit Account")

    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id','account_debit_id')
    def _compute_destination_account_id(self):
        for payment in self:
            if payment.invoice_ids:
                payment.destination_account_id = payment.invoice_ids[0].mapped(
                    'line_ids.account_id').filtered(
                        lambda account: account.user_type_id.type in ('receivable', 'payable'))[0]
            elif payment.payment_type == 'transfer':
                if not payment.company_id.transfer_account_id.id:
                    raise UserError(_('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
                payment.destination_account_id = payment.company_id.transfer_account_id.id
            elif payment.partner_id:
                if payment.partner_type == 'customer':
                    payment.destination_account_id = payment.partner_id.property_account_receivable_id.id
                else:
                    payment.destination_account_id = payment.partner_id.property_account_payable_id.id
            elif payment.partner_type == 'customer':
                default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
                payment.destination_account_id = default_account.id
            elif payment.partner_type == 'supplier':
                default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
                payment.destination_account_id = default_account.id
            if payment.account_debit_id:
                payment.destination_account_id = payment.account_debit_id.id
