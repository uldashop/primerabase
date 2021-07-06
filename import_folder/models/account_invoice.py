# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta
import json


class accountMove(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'
    
    import_ids = fields.Many2one('import.folder')#,store=True,compute='insertImport')
    
    @api.constrains('partner_id','invoice_line_ids','import_ids')
    def changeMandatory(self):
     
        for lines in self.invoice_line_ids:
            if lines.account_id.request_import == True and (self.import_ids == None or not self.import_ids.id) and self.type == 'in_invoice':
                raise ValidationError('No puede guardar si no escoje una carpeta de importacion.')

    # @api.one
    # @api.depends('payment_move_line_ids.amount_residual','outstanding_credits_debits_widget')
    # @api.onchange('payment_move_line_ids','outstanding_credits_debits_widget')
    # def insertImport(self):
    #     for inv in self:
    #         if json.loads(inv.payments_widget) != False:
    #                 for pay in json.loads(inv.payments_widget)['content']:
    #                     payment = self.env['account.payment'].browse(pay['account_payment_id'])
    #                     inv.import_ids = [(4, payment.import_ids.id)]
                        
     

class resPartner(models.Model):
    _name = 'account.account'
    _inherit = 'account.account'

    request_import = fields.Boolean('Solicita Carpeta de Importación')

    

