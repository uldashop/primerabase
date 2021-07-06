# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from datetime import date, datetime
from odoo.exceptions import UserError

class AccountCheque(models.Model):
    _name = "account.cheque"
    _order = 'id desc'

    sequence = fields.Char(string='Sequence', readonly=True ,copy=True, index=True)
    name = fields.Char(string="Name",required="1")
    bank_account_id = fields.Many2one('account.account','Bank Account')
    account_cheque_type = fields.Selection([('incoming','Incoming'),('outgoing','Outgoing')],string="Cheque Type")
    cheque_number = fields.Char(string="Cheque Number",required=True)
    amount = fields.Float(string="Amount",required=True)
    cheque_date = fields.Date(string="Cheque Date",default=datetime.now().date())
    cheque_given_date = fields.Date(string="Cheque Given Date")
    cheque_receive_date = fields.Date(string="Cheque Receive Date")
    cheque_return_date = fields.Date(string="Cheque Return Date")
    payee_user_id = fields.Many2one('res.partner',string="Payee",required="1")
    credit_account_id = fields.Many2one('account.account',string="Credit Account")
    debit_account_id = fields.Many2one('account.account',sring="Debit Account")
    comment = fields.Text(string="Comment")
    attchment_ids = fields.One2many('ir.attachment','account_cheque_id',string="Attachment")
    status = fields.Selection([('draft','Draft'),('registered','Registered'),('bounced','Bounced'),('return','Returned'),('cashed','Done'),('cancel','Cancel')],string="Status",default="draft",copy=False, index=True, track_visibility='onchange')
    
    status1 = fields.Selection([('draft','Draft'),('registered','Registered'),('bounced','Bounced'),('return','Returned'),('deposited','Deposited'),('cashed','Done'),('cancel','Cancel')],string="Status",default="draft",copy=False, index=True, track_visibility='onchange')
    
    journal_id = fields.Many2one('account.journal',string="Journal",required=True)
    company_id = fields.Many2one('res.company',string="Company",required=True)
    journal_items_count =  fields.Integer(compute='_active_journal_items',string="Journal Items") 
    # invoice_ids = fields.One2many('account.invoice','account_cheque_id',string="Invoices",compute="_count_account_invoice")
    attachment_count  =  fields.Integer('Attachments', compute='_get_attachment_count')
    '''journal_type = fields.Selection([('purchase_refund', 'Refund Purchase'), ('purchase', 'Create Supplier Invoice')], 'Journal Type', readonly=True, default=_get_journal_type)'''
    third_party_name = fields.Char('A nombre de Tercero',readonly=True, states={'draft': [('readonly', False)]})
    payment_id = fields.Many2one('account.payment',string="Pago")

    def print_checks(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        self = self.filtered(lambda r: r.payment_id.payment_method_id.code == 'check_printing' and r.payment_id.state != 'reconciled')

        if len(self) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
                              "not have already been reconciled"))
        if any(payment.journal_id != self[0].payment_id.journal_id for payment in self):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))

        # if not self[0].payment_id.journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            # last_printed_check = self.payment_id.search([
            #     ('journal_id', '=', self[0].payment_id.journal_id.id),
            #     ('check_number', '!=', 0)], order="check_number desc", limit=1)
            # next_check_number = last_printed_check and last_printed_check.check_number + 1 or 1
        return {
            'name': _('Print Pre-numbered Checks Payroll'),
            'type': 'ir.actions.act_window',
            'res_model': 'print.prenumbered.checks',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'payment_ids': self.payment_id.id,
                'default_next_check_number': self[0].cheque_number,
            }}
        # else:
        #     self.filtered(lambda r: r.payment_id.state == 'draft').post()
        #     return self.do_print_checks()
    
    @api.model 
    def default_get(self, flds): 
        result = super(AccountCheque, self).default_get(flds)
        res = self.env['res.config.settings'].sudo(1).search([], limit=1, order="id desc")
        if self._context.get('default_account_cheque_type') == 'incoming':
            result['credit_account_id'] = res.in_credit_account_id.id
            result['debit_account_id'] = res.in_debit_account_id.id
            result['journal_id'] = res.specific_journal_id.id
        else:
            result['credit_account_id'] = res.out_credit_account_id.id
            result['debit_account_id'] = res.out_debit_account_id.id
            result['journal_id'] = res.specific_journal_id.id 
        return result 
        
    def open_payment_matching_screen(self):
        # Open reconciliation view for customers/suppliers
        move_line_id = False
        account_move_line_ids = self.env['account.move.line'].search([('partner_id','=',self.payee_user_id.id)])
        for move_line in account_move_line_ids:
            if move_line.account_id.reconcile:
                move_line_id = move_line.id
                break;
        action_context = {'company_ids': [self.company_id.id], 'partner_ids': [self.payee_user_id.id]}
        if self.account_cheque_type == 'incoming':
            action_context.update({'mode': 'customers'})
        elif self.account_cheque_type == 'outgoing':
            action_context.update({'mode': 'suppliers'})
        if account_move_line_ids:
            action_context.update({'move_line_id': move_line_id})
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }
        
    # @api.multi
    # def _count_account_invoice(self):
    #     invoice_list = []
    #     for invoice in self.payee_user_id.invoice_ids:
    #         invoice_list.append(invoice.id)
    #         self.invoice_ids = [(6, 0, invoice_list)]
    #     return
        
    def _active_journal_items(self):
        list_of_move_line = []
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        for move in journal_item_ids:
            for line in move.line_ids:
                list_of_move_line.append(line.id)
        item_count = len(list_of_move_line)
        journal_items.journal_items_count = item_count
        return
        
    def action_view_jornal_items(self):
        self.ensure_one()
        list_of_move_line = []
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        for move in journal_item_ids:
            for line in move.line_ids:
                list_of_move_line.append(line.id)
        return {
            'name': 'Journal Items',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': [('id', '=', list_of_move_line)],
        }
        
    def _get_attachment_count(self):
        for cheque in self:
            attachment_ids = self.env['ir.attachment'].search([('account_cheque_id','=',cheque.id)])
            cheque.attachment_count = len(attachment_ids)
        
    def attachment_on_account_cheque(self):
        self.ensure_one()
        return {
            'name': 'Attachment.Details',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ir.attachment',
            'domain': [('account_cheque_id', '=', self.id)],
        }
        
    @api.model
    def create(self, vals):
        journal = self.env['account.journal'].browse(vals['journal_id'])
        sequence = journal.sequence_id
        vals['sequence'] = sequence.with_context(ir_sequence_date=datetime.today().date().strftime("%Y-%m-%d")).next_by_id()
        result = super(AccountCheque, self).create(vals)
        return result
        
    def set_to_submit(self):
        account_move_obj = self.env['account.move']
        for s in self:
            move_lines = []
            if s.account_cheque_type == 'incoming':
                vals = {
                        'name' : s.name,
                        'date' : s.cheque_receive_date,
                        'journal_id' : s.journal_id.id,
                        'company_id' : s.company_id.id,
                        'state' : 'draft',
                        'ref' : s.sequence + '- ' + s.cheque_number + '- ' + 'Registered',
                        'account_cheque_id' : s.id
                }
                account_move = account_move_obj.create(vals)
                debit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.debit_account_id.id, 
                        'debit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.credit_account_id.id, 
                        'credit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
                s.status1 = 'registered'
            else:
                vals = {
                        'name' : s.name,
                        'date' : s.cheque_given_date,
                        'journal_id' : s.journal_id.id,
                        'company_id' : s.company_id.id,
                        'state' : 'draft',
                        'ref' : s.sequence + '- ' + s.cheque_number + '- ' + 'Registered',
                        'account_cheque_id' : s.id
                }
                account_move = account_move_obj.create(vals)
                debit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.debit_account_id.id, 
                        'debit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.credit_account_id.id, 
                        'credit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
                s.status = 'registered'
            # return account_move

    def set_to_bounced(self):
        account_move_obj = self.env['account.move']
        for s in self:
            move_lines = []
            if s.account_cheque_type == 'incoming':
                vals = {
                        'name' : s.name,
                        'date' : s.cheque_receive_date,
                        'journal_id' : s.journal_id.id,
                        'company_id' : s.company_id.id,
                        'state' : 'draft',
                        'ref' : s.sequence + '- ' + s.cheque_number + '- ' + 'Bounced',
                        'account_cheque_id' : s.id
                }
                account_move = account_move_obj.create(vals)
                debit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.bank_account_id.id, 
                        'debit' : s.amount,
                        'amount_currency':0,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.payee_user_id.property_account_receivable_id.id, 
                        'credit' : s.amount,
                        'amount_currency':0,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
                s.status1 = 'bounced'
            else:
                vals = {
                        'name' : s.name,
                        'date' : s.cheque_given_date,
                        'journal_id' : s.journal_id.id,
                        'company_id' : s.company_id.id,
                        'state' : 'draft',
                        'ref' : s.sequence + '- ' + s.cheque_number + '- ' + 'Bounced',
                        'account_cheque_id' : s.id
                }
                account_move = account_move_obj.create(vals)
                debit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.payee_user_id.property_account_payable_id.id, 
                        'debit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'amount_currency':0,
                        'company_id' : s.company_id.id,
                        'payment_id': s.payment_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.debit_account_id.id, 
                        'credit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'amount_currency':0,
                        'company_id' : s.company_id.id,
                        'payment_id': s.payment_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
                account_move.post()
                s.status = 'bounced'
            # return account_move      

    def set_to_return(self):
        return_check = self.env['ir.default'].sudo().get("res.config.settings",'return_check_id',False,self.env.company.id)
        # deposite_account_id = self.env['ir.default'].sudo().get("res.config.settings",'deposite_account_id',False,self.env.company.id)
        if not return_check :
            raise UserError("Configure la Cuenta de Cheques Devueltos en Configuraciones")
        self.payment_id.state = 'draft'
        account_move_obj = self.env['account.move']
        move_lines = []
        list_of_move_line = [] 
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        
        matching_dict = []
        for move in journal_item_ids:
            for line in move.line_ids:
                if line.full_reconcile_id:
                    matching_dict.append(line)
                    #line.remove_move_reconcile()
                                    
        if len(matching_dict) != 0:
            rec_id = matching_dict[0].full_reconcile_id.id
            a = self.env['account.move.line'].search([('full_reconcile_id','=',rec_id)])
            
            for move_line in a:
                move_line.remove_move_reconcile()
        
        if self.account_cheque_type == 'incoming':
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_receive_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + ' ' + 'Devuelto',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : return_check, 
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : self.company_id.id,
                    'payment_id': self.payment_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.bank_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : self.company_id.id,
                    'payment_id': self.payment_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status1 = 'return'
            self.cheque_return_date = datetime.now().date()
        else:
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_given_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + ' ' + 'Devuelto',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.bank_account_id.id, 
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : self.company_id.id,
                    'payment_id': self.payment_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : self.company_id.id,
                    'payment_id': self.payment_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status = 'return'
            self.cheque_return_date = datetime.now().date()
        self.payment_id.state = 'posted'
        return account_move           

    def set_to_reset(self):
        account_move_obj = self.env['account.move']
        move_lines = []
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        journal_item_ids.unlink()
        if self.account_cheque_type == 'incoming':
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_receive_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Registered',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': s.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': s.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status1 = 'registered'
            self.cheque_return_date = datetime.now().date()
        else:
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_given_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Registered',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : self.company_id.id,
                    'payment_id': s.payment_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': s.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status = 'registered'
            self.cheque_return_date = datetime.now().date()
        return account_move                      

    def set_to_deposite(self):
        account_move_obj = self.env['account.move']
        for s in self:
            s.payment_id.state = 'draft'
            move_lines = []
            if s.account_cheque_type == 'incoming':
                vals = {
                        'name' : s.name,
                        'date' : s.cheque_receive_date,
                        'journal_id' : s.journal_id.id,
                        'company_id' : s.company_id.id,
                        'state' : 'draft',
                        'ref' : s.sequence + '- ' + s.cheque_number + ' ' + 'Depositado',
                        'account_cheque_id' : s.id
                }
                account_move = account_move_obj.create(vals)
                # res = s.env['res.config.settings'].sudo(1).search([], limit=1, order="id desc")
                deposite_id = self.env['ir.default'].sudo().get("res.config.settings",'deposite_account_id',False,self.env.company.id)
                if not s.bank_account_id:
                    if not deposite_id:
                        raise UserError("Por favor agregue la cuenta bancaria o configure la cuenta a depositar.")
                    s.bank_account_id = deposite_id
                
                debit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.bank_account_id.id, 
                        'debit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'amount_currency':0,
                        'payment_id': s.payment_id.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : s.payee_user_id.id,
                        'account_id' : s.debit_account_id.id, 
                        'credit' : s.amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'amount_currency':0,
                        'payment_id': s.payment_id.id,
                        'company_id' : s.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
                account_move.post()
                s.status1 = 'deposited'
                # return account_move          
            s.payment_id.state = 'posted'

    def set_to_cancel(self): 
        account_move_obj = self.env['account.move']
        move_lines = []
        self.payment_id.state = 'reconciled'
        vals = {
                'name' : self.name,
                'date' : self.cheque_receive_date,
                'journal_id' : self.journal_id.id,
                'company_id' : self.company_id.id,
                'state' : 'draft',
                'ref' : self.sequence + '- ' + self.cheque_number + ' ' + 'Cancelado',
                'account_cheque_id' : self.id
            }
        if self.account_cheque_type == 'incoming':       
            if self.status1 == 'registered':
                account_id = self.debit_account_id.id
            else:
                return_check = self.env['ir.default'].sudo().get("res.config.settings",'return_check_id',False,self.env.company.id)
                if not return_check :
                    raise UserError("Configure la Cuenta de Cheques Devueltos en Configuraciones")
                account_id = return_check
            self.status1 = 'cancel'
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.payee_user_id.property_account_receivable_id.id,
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': self.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : account_id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': self.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
        else:
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id,
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': self.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'payment_id': self.payment_id.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status = 'cancel'

    @api.model
    def create_batch_payment(self):
        # We use self[0] to create the batch; the constrains on the model ensure
        # the consistency of the generated data (same journal, same payment method, ...)
        pass
        # payment_ids = []
        # for payment in self:
        #     if payment.status1 != 'registered' and payment.account_cheque_type != 'incoming':
        #         raise UserError(_("Solo se pueden crear lotes de Cheques Recibidos y en estado Registrados"))
        #     payment_ids.append(payment.payment_id)
        # self.set_to_deposite()
        # if any([p.payment_type == 'transfer' for p in payment_ids]):
        #     raise UserError(
        #         _('You cannot make a batch payment with internal transfers. Internal transfers ids: %s')
        #         % ([p.id for p in self if p.payment_type == 'transfer'])
        #     )

        # batch = self.env['account.batch.payment'].create({
        #     'journal_id': self[0].journal_id.id,
        #     'payment_ids': [(4, payment.id, None) for payment in payment_ids],
        #     'payment_method_id': self[0].payment_id.payment_method_id.id,
        #     'batch_type': self[0].payment_id.payment_type,
        # })

        # return {
        #     "type": "ir.actions.act_window",
        #     "res_model": "account.batch.payment",
        #     "views": [[False, "form"]],
        #     "res_id": batch.id,
        # }

class ChequeWizard(models.TransientModel):
    _name = 'cheque.wizard'

    @api.model 
    def default_get(self, flds): 
        result = super(ChequeWizard, self).default_get(flds)
        account_cheque_id = self.env['account.cheque'].browse(self._context.get('active_id'))
        if account_cheque_id.account_cheque_type == 'outgoing':
            result['is_outgoing'] = True
        return result
        
    def create_cheque_entry(self):
        account_cheque = self.env['account.cheque'].browse(self._context.get('active_ids'))
        account_move_obj = self.env['account.move']
        move_lines = []
        if account_cheque.account_cheque_type == 'incoming':
            vals = {
                    'name' : account_cheque.name,
                    'date' : self.chequed_date,
                    'journal_id' : account_cheque.journal_id.id,
                    'company_id' : account_cheque.company_id.id,
                    'state' : 'draft',
                    'ref' : account_cheque.sequence + '- ' + account_cheque.cheque_number + '- ' + 'Cashed',
                    'account_cheque_id' : account_cheque.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : account_cheque.credit_account_id.id, 
                    'debit' : account_cheque.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : account_cheque.bank_account_id.id, 
                    'credit' : account_cheque.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_cheque.status1 = 'cashed'
        else:
            vals = {
                    'name' : account_cheque.name,
                    'date' : self.chequed_date,
                    'journal_id' : account_cheque.journal_id.id,
                    'company_id' : account_cheque.company_id.id,
                    'state' : 'draft',
                    'ref' : account_cheque.sequence + '- ' + account_cheque.cheque_number + '- ' + 'Cashed',
                    'account_cheque_id' : account_cheque.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : account_cheque.debit_account_id.id, 
                    'debit' : account_cheque.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : self.bank_account_id.id, 
                    'credit' : account_cheque.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_cheque.status = 'cashed'
        return account_move


    chequed_date = fields.Date(string="Cheque Date")
    bank_account_id = fields.Many2one('account.account',string="Bank Account")
    is_outgoing = fields.Boolean(string="Is Outgoing",default=False)
    
class ChequeTransferedWizard(models.TransientModel):
    _name = 'cheque.transfered.wizard'

    def create_ckeck_transfer_entry(self):
        account_cheque = self.env['account.cheque'].browse(self._context.get('active_ids'))
        account_move_obj = self.env['account.move']
        move_lines = []
        if account_cheque.account_cheque_type == 'incoming':
            vals = {
                    'name' : account_cheque.name,
                    'date' : self.transfered_date,
                    'journal_id' : account_cheque.journal_id.id,
                    'company_id' : account_cheque.company_id.id,
                    'state' : 'draft',
                    'ref' : account_cheque.sequence + '- ' + account_cheque.cheque_number + '- ' + 'Transfered',
                    'account_cheque_id' : account_cheque.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.contact_id.id,
                    'account_id' : account_cheque.credit_account_id.id, 
                    'debit' : account_cheque.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.contact_id.id,
                    'account_id' : account_cheque.debit_account_id.id, 
                    'credit' : account_cheque.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'amount_currency':0,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_cheque.status1 = 'transfered'
            return account_move
        
    transfered_date = fields.Date(string="Transfered Date")
    contact_id = fields.Many2one('res.partner',string="Contact")
    
class AccountMoveLine(models.Model):
    _inherit='account.move'

    account_cheque_id  =  fields.Many2one('account.cheque', 'Journal Item')

class ReportWizard(models.TransientModel):
    _name = "report.wizard"

    from_date = fields.Date('From Date', required = True)
    to_date = fields.Date('To Date',required = True)
    cheque_type = fields.Selection([('incoming','Incoming'),('outgoing','Outgoing')],string="Cheque Type",default='incoming')
    
    
    def submit(self):
        inc_temp = []
        out_temp = []
        temp = [] 
        
        if self.cheque_type == 'incoming':
            in_account_cheque_ids = self.env['account.cheque'].search([(str('cheque_date'),'>=',self.from_date),(str('cheque_date'),'<=',self.to_date),('account_cheque_type','=','incoming')])
        
            if not in_account_cheque_ids:
                raise UserError(_('There Is No Any Cheque Details.'))
            else:
                for inc in in_account_cheque_ids:
                    temp.append(inc.id)
            
        if self.cheque_type == 'outgoing':
            out_account_cheque_ids = self.env['account.cheque'].search([(str('cheque_date'),'>=',self.from_date),(str('cheque_date'),'<=',self.to_date),('account_cheque_type','=','outgoing')])
            
            if not out_account_cheque_ids:
                raise UserError(_('There Is No Any Cheque Details.'))
            else:
                for out in out_account_cheque_ids:
                    temp.append(out.id)
                               
        data = temp
        in_data = inc_temp
        out_data = out_temp
        datas = {
            'ids': self._ids,
            'model': 'account.cheque',
            'form': data,
            'from_date':self.from_date,
            'to_date':self.to_date,
            'cheque_type' : self.cheque_type,
        }
        return self.env.ref('bi_account_cheque.account_cheque_report_id').report_action(self,data=datas)

class IrAttachment(models.Model):
    _inherit='ir.attachment'

    account_cheque_id  =  fields.Many2one('account.cheque', 'Attchments')
    
