# -*- coding: utf-8 -*-
 
import os
import time
from jinja2 import Environment, FileSystemLoader
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta, datetime
from itertools import groupby
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import json
import re
import logging

from . import utils
from ..xades.sri import DocumentXML
from ..xades.xades import Xades
from .edoc import ManualAuth

TEMPLATES = {
    'out_invoice': 'out_invoice.xml',
    'out_refund': 'out_refund.xml',
    'out_debit': 'out_debit.xml',
    'liq_purchase': 'liq_purchase.xml'

}

_DOCUMENTOS_EMISION = ('out_invoice', 'liq_purchase', 'out_refund','out_debit', )
_DOCUMENTOS_RETENIBLES = (
    'out_invoice', 
    'in_invoice', 
    'out_refund', 
    'in_refund', 
    'out_debit',
    'in_debit',
    'sale_note',
    'liq_purchase',
    )

class AccountInvoice(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'account.edocument']
    _logger = logging.getLogger('account.edocument')

    sri_sent = fields.Boolean('Enviado', default=False)
    sri_errors = fields.One2many('sri.error','invoice_id', string='Errores SRI')
    invoice_line_dict = fields.Binary('Filtered lines for promo', compute="filter_promo_lines")

    def _get_amount_by_group(self):
        ''' Helper to get the taxes grouped according their account.tax.group.
        This method is only used when printing the invoice.
        '''
        for move in self:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_balance_multiplicator = -1 if move.is_inbound(True) else 1
            res = {}
            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in move.line_ids:
                if line.tax_line_id.tax_group_id.code not in ('vat', 'vat0', 'ice'): continue
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += tax_balance_multiplicator * (line.amount_currency if line.currency_id else line.balance)
                tax_key_add_base = tuple(move._get_tax_key_for_group_add_base(line))
                if tax_key_add_base not in done_taxes:
                    if line.currency_id and line.company_currency_id and line.currency_id != line.company_currency_id:
                        amount = line.company_currency_id._convert(line.tax_base_amount, line.currency_id, line.company_id, line.date or fields.Date.context_today(self))
                    else:
                        amount = line.tax_base_amount
                    res[line.tax_line_id.tax_group_id]['base'] += amount
                    # The base should be added ONCE
                    done_taxes.add(tax_key_add_base)
            # At this point we only want to keep the taxes with a zero amount since they do not
            # generate a tax line.
            zero_taxes = set()
            for line in move.line_ids:
                for tax in line.tax_ids.flatten_taxes_hierarchy():
                    if tax.tax_group_id not in res or tax.tax_group_id in zero_taxes:
                        res.setdefault(tax.tax_group_id, {'base': 0.0, 'amount': 0.0})
                        res[tax.tax_group_id]['base'] += tax_balance_multiplicator * (line.amount_currency if line.currency_id else line.balance)
                        zero_taxes.add(tax.tax_group_id)
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            return [(
                    group.name, amounts['amount'],
                    amounts['base'],
                    formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                    formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                    len(res),
                    group.id
                )
                for group, amounts in res
                if group.code in ('vat', 'vat0', 'ice')
            ]


    def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.type in _DOCUMENTOS_EMISION else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

    @api.depends('state', 'journal_id', 'date', 'invoice_date')
    def _compute_invoice_sequence_number_next(self):
        """ computes the prefix of the number that will be assigned to the first invoice/bill/refund of a journal, in order to
        let the user manually change it.
        """
        # Check user group.
        system_user = self.env.is_system()
        if not system_user:
            self.invoice_sequence_number_next_prefix = False
            self.invoice_sequence_number_next = False
            return

        # Check moves being candidates to set a custom number next.
        moves = self.filtered(lambda move: move.is_invoice() and move.name == '/')
        if not moves:
            self.invoice_sequence_number_next_prefix = False
            self.invoice_sequence_number_next = False
            return

        treated = self.browse()
        for key, group in groupby(moves, key=lambda move: (move.journal_id, move._get_sequence())):
            journal, sequence = key
            domain = [('journal_id', '=', journal.id), ('state', '=', 'posted')]
            if self.ids:
                domain.append(('id', 'not in', self.ids))
            if journal.type == 'sale':
                domain.append(('type', 'in', ('out_invoice', 'out_refund', 'out_debit', 'liq_purchase')))
            elif journal.type == 'purchase':
                domain.append(('type', 'in', ('in_invoice', 'in_refund', 'in_debit', 'sale_note')))
            else:
                continue
            if self.search_count(domain):
                continue

            for move in group:
                sequence_date = move.date or move.invoice_date
                prefix, dummy = sequence._get_prefix_suffix(date=sequence_date, date_range=sequence_date)
                number_next = sequence._get_current_sequence().number_next_actual
                move.invoice_sequence_number_next_prefix = prefix
                move.invoice_sequence_number_next = '%%0%sd' % sequence.padding % number_next
                treated |= move
        remaining = (self - treated)
        remaining.invoice_sequence_number_next_prefix = False
        remaining.invoice_sequence_number_next = False
    
    def _get_creation_message(self):
        # OVERRIDE
        if not self.is_invoice(include_receipts=True):
            return super()._get_creation_message()
        return {
            'out_invoice': _('Invoice Created'),
            'out_refund': _('Refund Created'),
            'in_invoice': _('Vendor Bill Created'),
            'in_refund': _('Credit Note Created'),
            'out_receipt': _('Sales Receipt Created'),
            'in_receipt': _('Purchase Receipt Created'),
            'sale_note': 'Nota de venta creada',
            'liq_purchase': 'Liquidacion de compra creada',
            'in_debit': 'Nota de debito creada',
            'out_debit': 'Nota de debito creada'
        }[self.type]

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund', 'in_refund', 'in_invoice', 'in_debit', 'out_debit', 'liq_purchase', 'sale_note'] + (include_receipts and ['out_receipt', 'in_receipt'] or [])

    def is_invoice(self, include_receipts=False):
        return self.type in self.get_invoice_types(include_receipts)

    @api.model
    def get_sale_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund', 'sale_note', 'out_debit'] + (include_receipts and ['out_receipt'] or [])

    def is_sale_document(self, include_receipts=False):
        return self.type in self.get_sale_types(include_receipts)

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ['in_invoice', 'in_refund', 'in_debit', 'liq_purchase'] + (include_receipts and ['in_receipt'] or [])

    def is_purchase_document(self, include_receipts=False):
        return self.type in self.get_purchase_types(include_receipts)

    @api.model
    def get_inbound_types(self, include_receipts=True):
        return ['out_invoice', 'in_refund', 'out_debit'] + (include_receipts and ['out_receipt'] or [])

    @api.model
    def get_outbound_types(self, include_receipts=True):
        return ['in_invoice', 'out_refund', 'in_debit', 'liq_purchase', 'sale_note'] + (include_receipts and ['in_receipt'] or [])

    def _get_sequence(self):
        ''' Return the sequence to be used during the post of the current move.
        :return: An ir.sequence record or False.
        '''
        self.ensure_one()

        journal = self.journal_id
        if self.type in ('entry', 'out_invoice', 'in_invoice', 'out_receipt', 'in_receipt') or not journal.refund_sequence:
            return journal.sequence_id
        if not journal.refund_sequence_id:
            return
        return journal.refund_sequence_id

    def _get_move_display_name(self, show_ref=False):
        ''' Helper to get the display name of an invoice depending of its type.
        :param show_ref:    A flag indicating of the display name must include or not the journal entry reference.
        :return:            A string representing the invoice.
        '''
        self.ensure_one()
        draft_name = ''
        if self.state == 'draft':
            draft_name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Credit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'liq_purchase': 'Liquidacion de compras',
                'sale_note': 'Nota de venta',
                'in_debit': 'Nota de Debito',
                'out_debit': 'Nota de Debito',
                'entry': _('Draft Entry'),
            }[self.type]
            if not self.name or self.name == '/':
                draft_name += ' (* %s)' % str(self.id)
            else:
                draft_name += ' ' + self.name
        return (draft_name or self.name) + (show_ref and self.ref and ' (%s%s)' % (self.ref[:50], '...' if len(self.ref) > 50 else '') or '')

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.

        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if not default_values_list:
            default_values_list = [{} for move in self]

        if cancel:
            lines = self.mapped('line_ids')
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()

        reverse_type_map = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'out_refund': 'entry',
            'in_invoice': 'in_refund',
            'in_refund': 'entry',
            'out_receipt': 'entry',
            'in_receipt': 'entry',
            'in_debit' : 'entry',
            'out_debit': 'entry',
            'liq_purchase': 'in_refund',
            'sale_note': 'in_refund'
        }

        move_vals_list = []
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'type': reverse_type_map[move.type],
                'reversed_entry_id': move.id,
            })
            
               
            move_vals_list.append(move._reverse_move_vals(default_values, cancel=cancel))

        reverse_moves = self.env['account.move'].create(move_vals_list)
        #raise UserError(reverse_moves[0].journal_id)
        for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False)):
            # Update amount_currency if the date has changed.
            if move.date != reverse_move.date:
                for line in reverse_move.line_ids:
                    if line.currency_id:
                        line._onchange_currency()
            reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
            reverse_move._onchange_journal()
        reverse_moves._check_balanced()

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel).post()
            for move, reverse_move in zip(self, reverse_moves):
                accounts = move.mapped('line_ids.account_id') \
                    .filtered(lambda account: account.reconcile or account.internal_type == 'liquidity')
                for account in accounts:
                    (move.line_ids + reverse_move.line_ids)\
                        .filtered(lambda line: line.account_id == account and line.balance)\
                        .reconcile()

        return reverse_moves


    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id and self.type in _DOCUMENTOS_EMISION:
            if self.type == 'out_invoice':
                self.auth_inv_id = self.journal_id.auth_out_invoice_id
            elif self.type == 'out_refund':
                self.auth_inv_id = self.journal_id.auth_out_refund_id
            elif self.type == 'liq_purchase':
                self.auth_inv_id = self.journal_id.auth_out_liq_purchase_id.id
            elif self.type == 'out_debit':
                self.auth_inv_id = self.journal_id.auth_out_debit_id.id
            # elif self.type == 'in_debit':
            #     self.auth_inv_id = self.journal_id.auth_in_debit_id.id
            self.auth_number = not self.auth_inv_id.is_electronic and self.auth_inv_id.name  # noqa
            number = '{0}'.format(
                str(self.auth_inv_id.sequence_id.number_next_actual).zfill(9)
            )
            self.reference = number
        return super(AccountInvoice, self)._onchange_journal()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Redefinicion de metodo para obtener:
        numero de autorizacion
        numero de documento
        El campo auth_inv_id representa la autorizacion para
        emitir el documento.
        """
        self = self.with_context(force_company=self.journal_id.company_id.id)
        #if not self.type:
        #    self.type = 'out_invoice'
        if self.type not in _DOCUMENTOS_EMISION:
            self.auth_inv_id = self.partner_id.get_authorisation(self.type)
            if not self.auth_inv_id.is_electronic:
                self.auth_number = self.auth_inv_id.name
            #self._recompute_dynamic_lines()
        warning = super(AccountInvoice, self)._onchange_partner_id()
        if warning:
            return warning

    @api.onchange('type','partner_id')
    def get_auth_inv_domain(self):
        map_type = {
            'in_invoice': '01',
            'sale_note': '02',
            'in_refund': '04',
            'liq_purchase': '03',
            'ret_in_invoice': '07',
            'in_debit': '05',
        }
        if self.type not in ('in_invoice', 'in_refund','liq_purchase','ret_in_invoice','in_debit'):
            return False
        else:
            if self.partner_id:
                auth = [auth for auth in self.partner_id.authorisation_ids if auth.type_id.code == map_type[self.type]]
                return {'domain':{'auth_inv_id':[('id','in', [ids.id for ids in tuple(auth) ])]}}

    @api.depends(
        'state',
        'reference'
    )
    def _compute_invoice_number(self):
        """
        Calcula el numero de factura segun el
        establecimiento seleccionado
        """
        for s in self:
            
            if s.type != 'entry' and s.reference and s.state!='draft':
                s.invoice_number = '{0}{1}{2}'.format(
                    s.auth_inv_id.serie_entidad,
                    s.auth_inv_id.serie_emision,
                    s.reference
                )
            else:
                s.invoice_number = '*'

    invoice_number = fields.Char(
        compute='_compute_invoice_number',
        string='Nro. Documento',
        store=True,
        readonly=True,
        copy=False
    )
    invoice_init_flag = fields.Boolean('Init', default=False, copy=False)
    internal_inv_number = fields.Char('Numero Interno', copy=False)
    auth_inv_id = fields.Many2one(
        'account.authorisation',
        string='Establecimiento',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Autorizacion para documento',
        copy=False
    )
    is_electronic = fields.Boolean('Es Electronico', compute="_get_electronic")
    auth_number = fields.Char('Autorización', copy=False)
    sustento_id = fields.Many2one(
        'account.ats.sustento',
        string='Sustento del Comprobante'
    )
    activity_limit_id = fields.Many2one('activity.limit', string='Actividad')
 
    retention_id = fields.Many2one(
        'account.retention',
        string='Retención de Impuestos',
        store=True, readonly=True,
        copy=False
    )
    has_retention = fields.Boolean(
        compute='_check_retention',
        string="Tiene Retención en IR",
        store=True,
        readonly=True
        )
    type = fields.Selection(selection_add=
        [
            ('liq_purchase', 'Liquidacion de Compra'),
            ('sale_note', 'Nota de venta'),
            ('in_debit', 'Nota de debito (Emision)'),
            ('out_debit', 'Nota de debito (Recepcion)'),
        ])
    withholding_number = fields.Char(
        'Num. Retención',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False
    )
    create_retention_type = fields.Selection(
        [
            ('auto', 'Automatico'),
            ('manual', 'Manual')
        ],
        string='Numerar Retención',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='auto'
    )
    reference = fields.Char('Num documento', copy=False, length=9)
    ats_earning_id=fields.Many2one('ats.earning', string="Tipo de ingreso exterior")
    amount_total_ec = fields.Monetary(string='Monto a recibir', store=True, readonly=True,
        compute='_compute_amount', copy=False)
    amount_retenido = fields.Monetary(string='Monto retenido', store=True, readonly=True,
        compute='_compute_amount', copy=False)

    auth_required = fields.Boolean('Tecnical field to determine if auth_number is required', compute='_get_electronic')

    @api.constrains('reference', 'type', 'partner_id', 'state', 'invoice_number')
    def check_invoice_number_constraint(self):
        for s in self:
            if s.type not in ['out_invoice', 'out_refund', 'out_debit']:
                if s.check_invoice_number():
                    continue
                else:
                    raise ValidationError('El numero de factura debe ser unico. {}'.format(s.invoice_number))
            continue
    
                
    def check_invoice_number(self):
        invoice_obj=self.env['account.move']
        if self.type == 'entry':
            return True
        #if self.state != 'draft':
        if self.type in ['out_invoice', 'out_refund', 'out_debit']:
            existing = invoice_obj.search([
                ('type', '=', self.type),
                ('company_id', '=', self.company_id.id),
                #('reference', '=', self.reference),
                ('auth_inv_id', '=', self.auth_inv_id.id),
                #('partner_id', '=', self.partner_id.id),
                ('invoice_number', '=', '{}{}{}'.format(self.auth_inv_id.serie_entidad, self.auth_inv_id.serie_emision, self.reference)),
                ('invoice_number', '!=', '*'),
                ('id', '!=', self.id)
            ])
        else:
            if self.state != 'draft':
                existing = invoice_obj.search([
                    ('type', '=', self.type),
                    ('partner_id', '=', self.partner_id.id),
                    ('invoice_number', '=', self.invoice_number),
                    ('id', '!=', self.id)
                ])
            else:
                existing=[]
        if len(existing):
            return False
        return True


    @api.depends('auth_inv_id', 'type')
    def _get_electronic(self):
        for s in self:
            if s.type not in ['entry', 'in_receipt', 'out_receipt']:
                s.auth_required = True
            else:
                s.auth_required = False
            if s.auth_inv_id and s.auth_inv_id.is_electronic:
                s.is_electronic = True
                if s.type in _DOCUMENTOS_EMISION:
                    s.auth_required = False
            else:
                s.is_electronic = False

    @api.onchange('reference')
    def _onchange_reference(self):
        # TODO: agregar validacion numerica a reference
        if self.reference:
            self.reference = self.reference.zfill(9)
            if not self.auth_inv_id.is_valid_number(self.reference):
                return {
                    'value': {
                        'reference': ''
                    },
                    'warning': {
                        'title': 'Error',
                        'message': u'Número no coincide con la autorización ingresada.'  # noqa
                    }
                }

    @api.constrains('auth_number')
    def check_reference(self):
        """
        Metodo que verifica la longitud de la autorizacion
        10: documento fisico
        35: factura electronica modo online
        49: factura electronica modo offline
        """
        for s in self:
            if s.type not in ['in_invoice', 'liq_purchase','in_debit','sale_note' ,'in_refund']:
                return
            if s.auth_number and len(s.auth_number) not in [10, 35, 49]:
                raise UserError(
                    u'Debe ingresar 10, 35 o 49 dígitos según el documento.'
                )
   
    def action_number(self):
        # TODO: ver donde incluir el metodo de numeracion
        #self.ensure_one()
        sequence = self.auth_inv_id.sequence_id
        if self.type not in ['out_invoice', 'liq_purchase', 'out_refund','out_debit']:#,'in_debit'
            return
        if not self.auth_inv_id:
            # asegura la autorizacion en el objeto
            self._onchange_journal()
            #self._onchange_partner()
        if self.check_invoice_number():
            if not self.invoice_init_flag:
                number = sequence.next_by_id()
            else:
                candidate = str(self.auth_inv_id.sequence_id.number_next_actual).zfill(9)
                if candidate == self.reference and self.is_electronic:
                    number = sequence.next_by_id()
                else:
                    number= self.reference
            self.write({'reference': number, 'internal_inv_number': number})
            self.env.cr.commit()
        else:
            raise ValidationError('El numero de factura debe ser unico. {}{}{}'.format(self.auth_inv_id.serie_entidad, self.auth_inv_id.serie_emision, self.reference))

    def verify_sale_note(self):
        for record in self:
            if record.type == 'sale_note':
                limit = record.activity_limit_id.amount
                if record.amount_total > limit:
                    raise UserError('La nota de venta supera el limite autorizado de $ %f.' % (limit,))

### Overrides

    def action_post(self):
        if self.mapped('line_ids.payment_id') and any(post_at == 'bank_rec' for post_at in self.mapped('journal_id.post_at')):
            raise UserError(_("A payment journal entry generated in a journal configured to post entries only when payments are reconciled with a bank statement cannot be manually posted. Those will be posted automatically after performing the bank reconciliation."))
        self.verify_sale_note()
        #self.action_date_assign()
        self.action_number()
        if self.type in _DOCUMENTOS_RETENIBLES:
            self.action_withholding_create()  
        for s in self:
            if s.type in ['in_invoice','in_refund'] and not s.auth_number:
                raise UserError(
                    u'Debe ingresar un número de autorización.'
                )      
        return self.post()

   
### /Overrides
    
    @api.depends('invoice_line_ids.tax_ids')
    def _check_retention(self):
        self.has_retention = False
        TAXES = ['ret_vat_b', 'ret_vat_srv', 'ret_ir', 'no_ret_ir']  # noqa
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                if tax.tax_group_id.code in TAXES:
                    self.has_retention = True

    def action_withholding_create(self):
        """
        Este método genera el documento de retencion en varios escenarios
        considera casos de:
        * Generar retencion automaticamente
        * Generar retencion de reemplazo
        * Cancelar retencion generada
        """
        TYPES_TO_VALIDATE = ['in_invoice', 'liq_purchase', 'in_debit']
        wd_number = False
        for inv in self:
            if not self.has_retention:
                continue

            # Autorizacion para Retenciones de la Empresa
            auth_ret = inv.journal_id.auth_retention_id
            if inv.type in ['in_invoice', 'liq_purchase', 'in_debit'] and not auth_ret:
                raise UserError(
                    u'No ha configurado la autorización de retenciones.'
                )

            if self.create_retention_type == 'manual':
                wd_number = inv.withholding_number

            # move to constrains ?
            if inv.create_retention_type == 'manual' and inv.withholding_number <= 0:  # noqa
                raise UserError(u'El número de retención es incorrecto.')
                # TODO: read next number

            #ret_taxes = inv.tax_line_ids.filtered(lambda l: l.tax_id.tax_group_id.code in ['ret_vat_b', 'ret_vat_srv', 'ret_ir'])  # noqa
            ret_taxes = []
            for line in self.invoice_line_ids:
                for tax in line.tax_ids:
                    tax_detail = tax.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
                    #raise UserError(str(tax_detail))
                    if tax.tax_group_id.code in ['ret_vat_b', 'ret_vat_srv', 'ret_ir']:
                        ret_taxes.append({
                            'group_id': tax.tax_group_id.id,
                            'tax_repartition_line_id': tax_detail[0]['tax_repartition_line_id'],
                            'amount': sum( [t['amount'] for t in tax_detail ]),
                            'base': sum( [t['base'] for t in tax_detail ]),
                            'tax_id': tax.id
                        })

            ret_taxes = sorted(ret_taxes, key = lambda x: x['tax_id'])
            ret_to_merge = groupby(ret_taxes, lambda x: x['tax_id'])
            ret_taxes = []
            for k,vv in ret_to_merge:
                v=list(vv)
                ret_taxes.append({
                            'group_id': v[0]['group_id'],
                            'tax_repartition_line_id': v[0]['tax_repartition_line_id'],
                            'amount': sum( [t['amount'] for t in v ]),
                            'base': sum( [t['base'] for t in v ]),
                            'tax_id': v[0]['tax_id']
                        })
            
            ret_taxes_orm = self.env['account.retention.line'].create(ret_taxes)
            if inv.retention_id:
                inv.retention_id.tax_ids = [(5,0,0)]
                ret_taxes_orm.write({
                    'retention_id': inv.retention_id.id,
                    'num_document': inv.invoice_number
                })
                #inv.retention_id.action_validate(wd_number)
                return True
            today = date.today()
            ret_date = inv.invoice_date
            #if today>ret_date:
            #    ret_date = today
            withdrawing_data = {
                'partner_id': inv.partner_id.id,
                'name': wd_number,
                'invoice_id': inv.id,
                'auth_id': auth_ret.id,
                'type': inv.type,
                'in_type': 'ret_%s' % inv.type,
                'date': ret_date,
                'manual': False
            }

            if len(ret_taxes) > 0:
                withdrawing = self.env['account.retention'].create(withdrawing_data)  # noqa

                ret_taxes_orm.write({'retention_id': withdrawing.id, 'num_document': inv.reference})  # noqa

                if inv.type in TYPES_TO_VALIDATE:
                    withdrawing.action_validate(wd_number)

                inv.write({'retention_id': withdrawing.id})
        return True

    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id:
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            if move.type in ['out_invoice', 'out_debit', 'out_credit', 'liq_purchase'] and move.autorizado_sri:
                raise UserError('No se puede regresar a borrador un documento recibido por el SRI.')
            if move.type in ['in_invoice', 'in_credit', 'in_debit'] and move.retention_id and move.retention_id.autorizado_sri:
                raise UserError('La retencion ha sido enviada al SRI, ya no se puede modificar el documento. Tiene que anular la retencion primero.')
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft'})

    def report_credit_note(self):
        return self.env.ref('l10n_ec.account_invoices_credit').report_action(self)
    
    def report_debit_note(self):
        return self.env.ref('l10n_ec.account_invoices_debit').report_action(self)

    def _merge_promos(self, lines):
        """

        'codigoPrincipal': codigoPrincipal,
                'descripcion': fix_chars(line.name.strip()),
                'cantidad': '%.6f' % (line.quantity),
                'precioUnitario': '%.6f' % (line.price_unit),
                'descuento': '%.2f' % discount,
                'precioTotalSinImpuesto': '%.2f' % (line.price_subtotal)

                """
        result=[]
        itered=[]
        def extract_name(item):
            name = item['descripcion']
            if ']' in name:
                return name.split('] ')[1].strip()
            if _('Free Product') in name:
                return name.split('- ')[1].strip()
            return name

        lines = sorted(lines, key=lambda l: -1*float(l['precioUnitario']))
        for line in lines:
            if float(line['precioUnitario']) < 0.0:

                for r in result:
                    new_val='%.2f' % (float(r['precioTotalSinImpuesto'])+float(line['precioTotalSinImpuesto']))
                    if extract_name(r) == extract_name(line) and r['precioTotalSinImpuesto'] != '0.00':
                        r.update({
                            'cantidad': str(float(r['cantidad'])-float(line['cantidad'])),
                            'precioTotalSinImpuesto': new_val
                        })
                        line.update({
                            'precioUnitario': '0.00',
                            'precioTotalSinImpuesto': '0.00'
                        })
                        for imp in line['impuestos']:
                            imp.update({
                                'baseImponible': '0.00',
                                'valor': '0.00'
                            })
                        for imp in r['impuestos']:
                            if imp['codigo']=='2':
                                imp.update({
                                    'baseImponible': new_val,
                                    'valor': '%.2f' % (float(new_val)*float(imp['tarifa'])/100.0)
                               })

                        result.append(line)
            else:
                result.append(line)

        return result

    @api.depends('invoice_line_ids')
    def filter_promo_lines(self):
        """
         <td style="border: 1px solid"><span t-esc="line.product_id.default_code or ' '"/></td>
                                <td style="border: 1px solid"><span t-esc="line.name or ' '"/></td>
                                <td style="border: 1px solid"><span t-esc="'%.2f' % line.price_unit"/></td>
                                <td style="border: 1px solid"><span t-esc="'%.2f' % line.quantity"/></td>
                                <td style="border: 1px solid"><span >0.00</span></td>
                                <td style="border: 1px solid"><span >0.00</span></td>
                                <td style="border: 1px solid"><span t-esc="'%.2f' % line.discount "/></td>
                                <td style="border: 1px solid"><span t-field="line.price_subtotal"
                                """
        result=[]
        itered=[]
        def extract_name(name):
            
            if ']' in name:
                return name.split('] ')[1].strip()
            if _('Free Product') in name:
                return name.split('- ')[1].strip()
            return name
        lines = sorted(self.invoice_line_ids, key=lambda l: -1*l.price_unit)
        for line in lines:
            if line.price_unit < 0.0:
                for r in result:
                    if extract_name(r['name']) == extract_name(line.name) and r['price_unit'] != '0.00':
                        r.update({
                            'quantity': '%.2f' % (float(r['quantity']) - float(line.quantity)),
                            'price_subtotal': float(r['price_subtotal']) + line.price_subtotal
                        })
                        result.append({
                            'default_code': line.product_id.default_code or ' ',
                            'price_unit': '0.00',
                            'quantity': '%.2f' % line.quantity,
                            'discount': '%.2f' % line.discount,
                            'name': line.name,
                            'price_subtotal': 0.00
                        })
            else:
                result.append({
                    'default_code': line.product_id.default_code or ' ',
                    'price_unit': '%.2f' % line.price_unit,
                    'quantity': '%.2f' % line.quantity,
                    'discount': '%.2f' % line.discount,
                    'name': line.name,
                    'price_subtotal': line.price_subtotal
                })
        self.invoice_line_dict = result

    def _info_factura(self, invoice):
        """
        """
        def fix_date(fecha):
            d = '{0:%d/%m/%Y}'.format(fecha)
            return d

        def sum_tax_groups(groups):
            return sum([t[0] for t in self.amount_by_group if t[1] in groups])

        company = invoice.company_id
        partner = invoice.partner_id
        infoFactura = {
            'fechaEmision': fix_date(invoice.invoice_date),
            'dirEstablecimiento': company.street.replace('&','&amp;'),
            'obligadoContabilidad': 'SI',
            'tipoIdentificacionComprador': utils.tipoIdentificacion[partner.type_identifier],  # noqa
            'razonSocialComprador': partner.name.replace('&','&amp;'),
            'identificacionComprador': partner.identifier,
            'direccionComprador': ' '.join([partner.street or '', partner.street2 or '']).replace('\n','').replace('\r\n','').replace('&','&amp;'),
            'totalSinImpuestos': '%.2f' % (invoice.amount_untaxed),
            'totalDescuento': '0.00',
            'propina': '0.00',
            'importeTotal': '{:.2f}'.format(invoice.amount_total),
            'moneda': 'DOLAR',
            'formaPago': invoice.epayment_id.code,
            'valorRetIva': '{:.2f}'.format(abs(sum_tax_groups(['ret_vat_srv', 'ret_vat_b']))),  # noqa
            'valorRetRenta': '{:.2f}'.format(abs(sum_tax_groups(['ret_ir']))),
            # 'Resolucion':company.resolution_number,
            # 'ret_agent': company.withholding_agent
        }
        if company.company_registry:
            infoFactura.update({'contribuyenteEspecial':
                                company.company_registry})
        else:
            raise UserError('No ha determinado si es contribuyente especial.')

        totalConImpuestos = []
        for tax in invoice.line_ids.filtered(lambda t: t.tax_line_id):
            if tax.tax_group_id.code in ['vat', 'vat0']:
            
                totalImpuesto = {
                    'codigo': utils.tabla17[tax.tax_group_id.code],
                    'codigoPorcentaje': utils.tabla18[str(tax.tax_line_id.amount).split('.')[0]],
                    'baseImponible': '{:.2f}'.format(tax.tax_base_amount),
                    'tarifa': tax.tax_line_id.amount,
                    'valor': '{:.2f}'.format(abs(tax.price_total))
                    }
                totalConImpuestos.append(totalImpuesto)
            if tax.tax_group_id.code in ['irbp']:
                
                    totalImpuesto = {
                        'codigo': '5',
                        'codigoPorcentaje': '5001',
                        'baseImponible': '{:.2f}'.format(tax.tax_base_amount),
                        'tarifa': '0.02',
                        'valor': '{:.2f}'.format(abs(tax.price_total))
                        }
                    totalConImpuestos.append(totalImpuesto)

            #if tax.group_id.code in ['ice']:
            #    totalImpuesto = {
            #        'codigo': utils.tabla17[tax.group_id.code],
            #        'codigoPorcentaje': tax.tax_id.description,
            #        'baseImponible': '{:.2f}'.format(tax.amount/(float(tax.percent_report)/100.0)),
            #        'tarifa': tax.percent_report,
            #        'valor': '{:.2f}'.format(tax.amount)
            #        }
            #    totalConImpuestos.append(totalImpuesto)
    
        infoFactura.update({'totalConImpuestos': totalConImpuestos})

        compensaciones = False
        #comp = self.compute_compensaciones()
        #if comp:
        #    compensaciones = True
        #    infoFactura.update({
        #        'compensaciones': compensaciones,
        #        'comp': comp
        #    })

        if self.type == 'out_refund':
            inv = self.reversed_entry_id
            inv_number = '{0}-{1}-{2}'.format(inv.invoice_number[:3], inv.invoice_number[3:6], inv.invoice_number[6:])  # noqa
            notacredito = {
                'codDocModificado': inv.auth_inv_id.type_id.code,
                'numDocModificado': inv_number,
                'motivo': self.ref,
                'fechaEmisionDocSustento': fix_date(inv.invoice_date),
                'valorModificacion': '{:.2f}'.format(self.amount_total)
            }
            infoFactura.update(notacredito)
      
      
        if self.type == 'out_debit':
            inv = self.search([('id', '=', self.id)], limit=1)
            inv_n = self.reversed_entry_id
            inv_number = '{0}-{1}-{2}'.format(inv_n.invoice_number[:3], inv_n.invoice_number[3:6], inv_n.invoice_number[6:])  # noqa
            impuesto=self._detalles_debit(invoice)
            infoFactura.update(impuesto)

            infoFactura.update({'contribuyenteEspecial':partner.property_account_position_id.name})
            infoFactura.update({'dirEstablecimiento': partner.street})
            
            pagos={ 'pago':{'importeTotal': '{:.2f}'.format(invoice.amount_total),
                            'formaPago': invoice.epayment_id.code}}
            infoFactura.update(pagos)
            infoFactura.update({'totalSinImpuestos': '%.2f' % (inv.amount_untaxed)})
            notadebito = {
                'codDocModificado': inv.auth_inv_id.type_id.code,
                'numDocModificado': inv_number,
                'motivo': self.name,
                'baseImponible': '{:.2f}'.format(inv.amount_untaxed),
                'fechaEmisionDocSustento': fix_date(inv.invoice_date or self.invoice_date),
                'valorModificacion': '{:.2f}'.format(self.amount_total)
            }
            infoFactura.update(notadebito)

        if self.type == 'liq_purchase':
            infoFactura.update({'tipoIdentificacionProveedor': utils.tipoIdentificacion[partner.type_identifier],  # noqa
                                'razonSocialProveedor': partner.name.replace('&','&amp;'),
                                'direccionProveedor': partner.street.replace('&','&amp;'),
                                'identificacionProveedor': partner.identifier,})
            if company.company_registry:
                infoFactura.update({'contribuyenteEspecial':
                                    company.company_registry})
            else:
                raise UserError('No ha determinado si es contribuyente especial.')

            pagos={ 'pago':{'importeTotal': '{:.2f}'.format(invoice.amount_total),
                            'formaPago': invoice.epayment_id.code}}
            infoFactura.update(pagos)

        return infoFactura

    def format_nc_number(self, val):
        if val:
            inv = self.search([('number', '=', val)], limit=1)
            inv_number = '{0}-{1}-{2}'.format(inv.invoice_number[:3], inv.invoice_number[3:6], inv.invoice_number[6:])  # noqa
            return inv_number
        else: return ''

    def nc_type(self, val):
        if val:
            inv = self.search([('number', '=', val)], limit=1)
            return inv.auth_inv_id.type_id.code
        else: return ''

    def nc_orig_date(self,val):
        if val:
            inv = self.search([('number', '=', val)], limit=1)
            return inv.invoice_date
        else: return ''

    def format_nd_number(self, val):
        if val:
            inv = self.search([('number', '=', val)], limit=1)
            inv_number = '{0}-{1}-{2}'.format(inv.invoice_number[:3], inv.invoice_number[3:6], inv.invoice_number[6:])  # noqa
            return inv_number
        else: return ''

    def nd_type(self, val):
        if val:
            inv = self.search([('number', '=', val)], limit=1)
            return inv.auth_inv_id.type_id.code
        else: return ''

    def nd_orig_date(self,val):
        inv = self.search([('number', '=', val)], limit=1)
        return inv.invoice_date

            
    @api.model
    def _get_tax_amount_by_group(self):
        totalConImpuestos = []
        for tax in self.tax_line_ids:
            if tax.group_id.code in ['vat', 'vat0', 'ice']:
                totalImpuesto = (tax.group_id.code, tax.amount)
                totalConImpuestos.append(totalImpuesto)
        return totalConImpuestos

    def _detalles_debit(self, invoice):
        """
        """
        def fix_chars(code):
            special = [
                [u'%', ' '],
                [u'º', ' '],
                [u'Ñ', 'N'],
                [u'ñ', 'n'],
                [u'&', '&amp;']
            ]
            for f, r in special:
                code = code.replace(f, r)
            return code
        for line in invoice.invoice_line_ids:           
            impuestos = []
            for tax_line in line.tax_ids:
                if tax_line.tax_group_id.code in ['vat', 'vat0']:
                    impuesto = {
                        'type': 'vat',
                        'codigo': utils.tabla17[tax_line.tax_group_id.code],
                        'codigoPorcentaje': utils.tabla18[str(tax_line.amount).split('.')[0]],  # noqa
                        'tarifa': tax_line.amount,
                        'baseImponible': '{:.2f}'.format(line.price_subtotal),
                        'valor': '{:.2f}'.format(line.price_subtotal *
                                                 tax_line.amount/100.0)
                    }
                    impuestos.append(impuesto)
           
            valorTotal=line.price_subtotal+(line.price_subtotal * tax_line.amount/100.0)
        return {'impuestos': impuestos,
                'valorTotal':'{:.2f}'.format(valorTotal)}
    
    def _detalles(self, invoice):
        """
        """
        def fix_chars(code):
            special = [
                [u'%', ' '],
                [u'º', ' '],
                [u'Ñ', 'N'],
                [u'ñ', 'n'],
                [u'&', '&amp;']
            ]
            for f, r in special:
                code = code.replace(f, r)
            return code
        
        detalles = []
        for line in invoice.invoice_line_ids:
            codigoPrincipal = line.product_id and \
                line.product_id.default_code and \
                fix_chars(line.product_id.default_code) or '001'
            priced = line.price_unit * (1 - (line.discount or 0.00) / 100.0)
            discount = (line.price_unit - priced) * line.quantity
            detalle = {
                'codigoPrincipal': codigoPrincipal,
                'descripcion': fix_chars(line.name.strip().replace('\n', ''))[:254],
                'cantidad': '%.6f' % (line.quantity),
                'precioUnitario': '%.6f' % (line.price_unit),
                'descuento': '%.2f' % discount,
                'precioTotalSinImpuesto': '%.2f' % (line.price_subtotal)
            }
            impuestos = []
            for tax_line in line.tax_ids:
                if tax_line.tax_group_id.code in ['vat', 'vat0']:
                    impuesto = {
                        'type': 'vat',
                        'codigo': utils.tabla17[tax_line.tax_group_id.code],
                        'codigoPorcentaje': utils.tabla18[str(tax_line.amount).split('.')[0]],  # noqa
                        'tarifa': tax_line.amount,
                        'baseImponible': '{:.2f}'.format(line.price_subtotal),
                        'valor': '{:.2f}'.format(line.price_subtotal *
                                                 tax_line.amount/100.0)
                    }
                    impuestos.append(impuesto)
                    
                if tax_line.tax_group_id.code in ['irbp']:
                
                    impuesto = {
                        'type': 'irbp',
                        'codigo': '5',
                        'codigoPorcentaje': '5001',
                        'baseImponible': '{:.2f}'.format(line.price_subtotal),
                        'tarifa': '0.02',
                        'valor': '{:.2f}'.format(tax_line._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))
                        }
                    impuestos.append(impuesto)
                    

                #if tax_line.tax_group_id.code in ['ice']:
                ##    product =  line.product_id
                #    ice_base = max(product.standard_price*1.25*line.quantity, line.price_subtotal/(1.0515))
                #    impuesto = {
                #        'type': 'ice',
                #        'codigo': utils.tabla17[tax_line.tax_group_id.code],
                #        'codigoPorcentaje': tax_line.description,
                #        
                #        'tarifa': tax_line.percent_report,
                #        'baseImponible': '{:.2f}'.format(ice_base),
                #        'valor': '{:.2f}'.format(ice_base *
                #                                 float(tax_line.percent_report)/100.0)
                #
                #    }
                #    
                #    impuestos.append(impuesto)

            ice = [imp for imp in impuestos if imp['type']=='ice']
            vat = [imp for imp in impuestos if imp['type']=='vat']
            if len(ice)>0:
                ice = ice[0]
                if len(vat)>0:
                    vat=vat[0]
                    vatbase = float(vat['baseImponible']) + float(ice['valor'])
                    tarifa = float(vat['tarifa'])
                    vat.update({
                        'baseImponible': '{:.2f}'.format(vatbase),
                        'valor': '{:.2f}'.format(vatbase * tarifa/100.0)
                    })    
                    impuestos = [vat,ice]
            detalle.update({'impuestos': impuestos})
            detalles.append(detalle)
            detalles = self._merge_promos(detalles)
        if invoice.type == 'out_debit':
            return {'motivo':'None',
                    'valor':invoice.amount_untaxed,
                    'Direccion':invoice.company_id.street,
                    'Email':invoice.company_id.email,
                    'Telefono':invoice.company_id.phone,
                    # 'Resolucion':invoice.company_id.resolution_number
                    }
        return {'detalles': detalles}

    
    def correct_ice(self, impuestos):
        ice = [imp for imp in impuestos if imp.type=='ice']
        vat = [imp for imp in impuestos if imp.type=='vat']
        if len(ice)>0:
            ice = ice[0]
            if len(vat)>0:
                vat=vat[0]
                vat.update({

                })
    
    def _compute_discount(self, detalles):
        total = sum([float(det['descuento']) for det in detalles['detalles']])
        return {'totalDescuento': '{:.2f}'.format(total)}

    def render_document(self, invoice, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template(TEMPLATES[self.type])
        data = {}
        data.update(self._info_tributaria(invoice, access_key, emission_code))
        data.update(self._info_factura(invoice))
        if self.type == 'out_debit':
            detalles = self._detalles(invoice)
            data.update(detalles)
        else:
            detalles = self._detalles(invoice)
            data.update(detalles)
            data.update(self._compute_discount(detalles))
        einvoice = einvoice_tmpl.render(data)
        
        return einvoice

    def render_authorized_einvoice(self, autorizacion):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template('authorized_einvoice.xml')
        if autorizacion.fechaAutorizacion != '':
            aut_date = str(autorizacion.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S"))
        else:
             aut_date = ''
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion,
            'ambiente': autorizacion.ambiente,
            'fechaAutorizacion': aut_date,
            'comprobante': autorizacion.comprobante
        }
        auth_invoice = einvoice_tmpl.render(auth_xml)
        return auth_invoice

    
    def action_generate_access_key(self):
        for obj in self:
            if obj.type not in ['out_invoice', 'out_refund','out_debit','liq_purchase']:#,'in_debit'
                continue
            if not obj.auth_inv_id.is_electronic:
                continue
            #obj.check_date(obj.invoice_date)
            obj.check_before_sent()
            access_key, emission_code = obj._get_codes(name='account.move')
            obj.write({'numero_autorizacion': access_key, 'clave_acceso': access_key})
        self.env.cr.commit()

    
    def action_generate_einvoice(self):
        """
        Metodo de generacion de factura electronica
        TODO: usar celery para enviar a cola de tareas
        la generacion de la factura y envio de email
        """
        for obj in self:
            #if obj.type not in ['out_invoice', 'out_refund']:
            #   continue
            if obj.is_electronic and not obj.clave_acceso:
                obj.action_generate_access_key()
        
            #obj.check_date(obj.invoice_date)
            obj.check_before_sent()
            #access_key, emission_code = obj._get_codes(name='account.invoice')
            access_key = obj.numero_autorizacion
            einvoice = obj.render_document(obj, access_key, self.company_id.emission_code)
            #print(einvoice,'einvoice')
            inv_xml = DocumentXML(einvoice, obj.type)
            inv_xml.validate_xml()
            xades = Xades()
            file_pk12 = obj.company_id.electronic_signature
            password = obj.company_id.password_electronic_signature
            signed_document = xades.sign(einvoice, file_pk12, password) 
            self.SriServiceObj.set_active_env(self.company_id.env_service)
            try:
                ok, errores = inv_xml.send_receipt(signed_document)
            except Exception as e:
                raise UserError(e)
            if not ok:
                if not "REGISTRAD" in errores:
                    #obj.sri_sent = True
                    err_obj=obj.env['sri.error']
                    err_obj.create({
                        'message': errores,
                        'state': 'error',
                        'invoice_id': obj.id
                    })
                    obj.env.cr.commit()
                    return {
                        'name': 'Error SRI',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'view_id': obj.env.ref('l10n_ec.sri_error_view')[0].id,
                        'res_model': 'account.move',
                        'src_model': 'account.move',
                        'context': "{}",
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'readonly': True,
                        'res_id': obj.id
                    }
            obj.sri_sent=True
            obj.authorize_einvoice()
                

    
    def authorize_einvoice(self):
        for obj in self:
            einvoice = obj.render_document(obj, obj.clave_acceso, obj.company_id.emission_code)
            inv_xml = DocumentXML(einvoice, obj.type)
            auth = None
            try:
                auth, m = inv_xml.request_authorization(obj.clave_acceso)
            except Exception as e:
                raise UserError(e)
            if not auth:
                #raise UserError(m)
                auth = ManualAuth()
                auth.numeroAutorizacion = obj.clave_acceso
                auth.estado = "EN PROCESO"
                if obj.company_id.env_service == '1':
                    auth.ambiente = "Pruebas"
                else:
                    auth.ambiente = "Produccion"
                auth.autorizado_sri = False
                auth.fechaAutorizacion = ''
                auth.comprobante = ''
            auth_einvoice = obj.render_authorized_einvoice(auth)
            obj.update_document(auth, [obj.clave_acceso, obj.company_id.emission_code])
            attach = obj.add_attachment(auth_einvoice, auth)
            message = """
            DOCUMENTO ELECTRONICO GENERADO <br><br>
            CLAVE DE ACCESO: %s <br>
            NUMERO DE AUTORIZACION %s <br>
            FECHA AUTORIZACION: %s <br>
            ESTADO DE AUTORIZACION: %s <br>
            AMBIENTE: %s <br>
            """ % (
                obj.clave_acceso,
                obj.numero_autorizacion,
                obj.fecha_autorizacion,
                obj.estado_autorizacion,
                obj.ambiente
            )
            obj.message_post(body=message)
            if obj.type == 'out_invoice':
                tmpl = 'l10n_ec.email_template_einvoice'
            if obj.type == 'out_refund':
                tmpl = 'l10n_ec.email_template_ecredit_note'
            if obj.type == 'out_debit':
                tmpl = 'l10n_ec.email_template_edebit_note'
            if obj.type == 'liq_purchase':
                tmpl = 'l10n_ec.email_template_eliq_purchase'
            obj.send_document(
                attachments=attach, #[a for a in attach],
                tmpl=tmpl
            )

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        ''' Compute the dynamic tax lines of the journal entry.

        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id
            if move.is_invoice(include_receipts=True):
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                if base_line.currency_id:
                    price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                    price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr, move.company_id.currency_id, move.company_id, move.date)
                else:
                    price_unit_foreign_curr = 0.0
                    price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                quantity = 1.0
                price_unit_foreign_curr = base_line.amount_currency
                price_unit_comp_curr = base_line.balance

            balance_taxes_res = base_line.tax_ids._origin.compute_all(
                price_unit_comp_curr,
                currency=base_line.company_currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=self.type in ('out_refund', 'in_refund'),
            )

            if base_line.currency_id:
                # Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
                amount_currency_taxes_res = base_line.tax_ids._origin.compute_all(
                    price_unit_foreign_curr,
                    currency=base_line.currency_id,
                    quantity=quantity,
                    product=base_line.product_id,
                    partner=base_line.partner_id,
                    is_refund=self.type in ('out_refund', 'in_refund'),
                )
                for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
                    tax = self.env['account.tax'].browse(b_tax_res['id'])
                    b_tax_res['amount_currency'] = ac_tax_res['amount']

                    # A tax having a fixed amount must be converted into the company currency when dealing with a
                    # foreign currency.
                    if tax.amount_type == 'fixed':
                        b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'], move.company_id.currency_id, move.company_id, move.date)

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                line.tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            line.tag_ids = compute_all_vals['base_tags']

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                if self.type == 'out_invoice' and tax.tax_group_id.code in ('ret_ir', 'ret_vat_srv', 'ret_vat_b'):
                    continue

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['balance'] += tax_vals['amount']
                taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
                taxes_map_entry['tax_base_amount'] += tax_vals['base']
                taxes_map_entry['grouping_dict'] = grouping_dict
            line.tax_exigible = tax_exigible

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # Don't create tax lines with zero balance.
            #if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(taxes_map_entry['amount_currency']):
            #    taxes_map_entry['grouping_dict'] = False

            tax_line = taxes_map_entry['tax_line']
            tax_base_amount = -taxes_map_entry['tax_base_amount'] if self.is_inbound() else taxes_map_entry['tax_base_amount']

            if not tax_line and not taxes_map_entry['grouping_dict']:
                continue
            elif tax_line and recompute_tax_base_amount:
                tax_line.tax_base_amount = tax_base_amount
            elif tax_line and not taxes_map_entry['grouping_dict']:
                # The tax line is no longer used, drop it.
                self.line_ids -= tax_line
            elif tax_line:
                if self.type == 'out_invoice' and tax_line.tax_group_id.code in ('ret_ir', 'ret_vat_srv', 'ret_vat_b'):
                    self.line_ids-=tax_line
                    taxes_map_entry['grouping_dict'] = False
                else:
                    tax_line.update({
                        'amount_currency': taxes_map_entry['amount_currency'],
                        'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                        'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                        'tax_base_amount': tax_base_amount,
                    })
                 
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                tax_line = create_method({
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'quantity': 1.0,
                    'date_maturity': False,
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                tax_line._onchange_amount_currency()
                tax_line._onchange_balance()


    @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id')
    def _compute_invoice_taxes_by_group(self):
        ''' Helper to get the taxes grouped according their account.tax.group.
        This method is only used when printing the invoice.
        '''
        for move in self:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id)
            res = {}
            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in tax_lines:
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += line.price_subtotal
                tax_key_add_base = tuple(move._get_tax_key_for_group_add_base(line))
                if tax_key_add_base not in done_taxes:
                    if line.currency_id and line.company_currency_id and line.currency_id != line.company_currency_id:
                        amount = line.company_currency_id._convert(line.tax_base_amount, line.currency_id, line.company_id, line.date or fields.Date.today())
                    else:
                        amount = line.tax_base_amount
                    res[line.tax_line_id.tax_group_id]['base'] += amount
                    # The base should be added ONCE
                    done_taxes.add(tax_key_add_base)

            # At this point we only want to keep the taxes with a zero amount since they do not
            # generate a tax line.
            for line in move.line_ids:
                for tax in line.tax_ids.filtered(lambda t: t.amount == 0.0 or (t.tax_group_id.code in ('ret_ir', 'ret_vat_srv', 'ret_vat_b') and move.type == 'out_invoice')):
                    res.setdefault(tax.tax_group_id, {'base': 0.0, 'amount': 0.0})
                    res[tax.tax_group_id]['base'] += line.price_subtotal
                    vals = sum([t['amount'] for t in tax.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, move.partner_id)['taxes']])
                    res[tax.tax_group_id]['amount'] += vals
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            move.amount_by_group = [(
                group.name, amounts['amount'],
                amounts['base'],
                formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
                group.id
            ) for group, amounts in res]

    