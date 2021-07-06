# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from ast import literal_eval

'''class CreditDebitJournal(models.Model):
    _name = 'credit.debit.journal'
    
    name = fields.Char(String="Name",default = "Products")
    credit_journal_ids = fields.Many2many('account.journal', 'credit_id','jou_id','credit_jornal',string='Credit Journal')
    debit_journal_ids = fields.Many2many('account.journal', 'debit_id','jou_id','debit_jornal',string='Debit Journal')

    @api.model
    def default_get(self,fields):
        journal_id = self.search([], limit=1, order="id desc")
        res = super(CreditDebitJournal, self).default_get(fields)
        credit_journal_list = []
        debit_journal_list = []
        
        if journal_id:
            for credit_journals in journal_id.credit_journal_ids:
                credit_journal_list.append(credit_journals.id)
            res.update(
                {
                    'credit_journal_ids':[(6,0,credit_journal_list)],
                }
            )
            
            for debit_journals in journal_id.debit_journal_ids:
                debit_journal_list.append(debit_journals.id)
            res.update(
                {
                    'debit_journal_ids':[(6,0,debit_journal_list)],
                }
            )
        return res  '''  
        
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    in_credit_account_id = fields.Many2one('account.account',string="Credit Account",company_dependent=True)
    in_debit_account_id = fields.Many2one('account.account',string="Debit Account",company_dependent=True)
    
    out_credit_account_id = fields.Many2one('account.account',string="Credit Account",company_dependent=True)
    out_debit_account_id = fields.Many2one('account.account',string="Debit Account",company_dependent=True)
    
    deposite_account_id = fields.Many2one('account.account',string="Deposite Account",company_dependent=True)
    specific_journal_id = fields.Many2one('account.journal',string="Specific Journal",company_dependent=True)

    return_check_id = fields.Many2one('account.account',string="Return Check Account",company_dependent=True)
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.default'].sudo()
        in_credit_account_id = ICPSudo.get("res.config.settings",'in_credit_account_id',False,self.env.company.id)
        in_debit_account_id = ICPSudo.get("res.config.settings",'in_debit_account_id',False,self.env.company.id)
        out_credit_account_id = ICPSudo.get("res.config.settings",'out_credit_account_id',False,self.env.company.id)
        out_debit_account_id = ICPSudo.get("res.config.settings",'out_debit_account_id',False,self.env.company.id)
        deposite_account_id = ICPSudo.get("res.config.settings",'deposite_account_id',False,self.env.company.id)
        specific_journal_id = ICPSudo.get("res.config.settings",'specific_journal_id',False,self.env.company.id)
        return_check_id = ICPSudo.get("res.config.settings",'return_check_id',False,self.env.company.id)
        
        res.update(
            in_credit_account_id=in_credit_account_id,
            in_debit_account_id=in_debit_account_id,
            out_credit_account_id=out_credit_account_id,
            out_debit_account_id=out_debit_account_id,
            deposite_account_id=deposite_account_id,
            specific_journal_id=specific_journal_id,
            return_check_id=return_check_id,
            )
        return res


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.default'].sudo()
        ICPSudo.set("res.config.settings",'in_credit_account_id',self.in_credit_account_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'in_debit_account_id',self.in_debit_account_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'out_credit_account_id',self.out_credit_account_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'out_debit_account_id',self.out_debit_account_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'deposite_account_id',self.deposite_account_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'specific_journal_id',self.specific_journal_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'return_check_id',self.return_check_id.id,False,self.env.company.id)

        
