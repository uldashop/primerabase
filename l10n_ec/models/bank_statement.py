# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

class accountBankStatement(models.Model):
    _inherit = 'account.bank.statement.line'

    operation =  fields.Selection([('D', 'Debito'),
                                    ('C','Credito'),
                                    ('+','Credito'),
                                    ('-','Debito'),
                                    ('NOTA DE CREDITO','Credito'),
                                    ('NOTA DE DEBITO','Debito'),
                                    ('CHEQUE','Cheque'),
                                    ('DEPOSITO','Deposito')],string="Tipo Transaccion")
    date_hour =  fields.Datetime('Fecha/Hora')

    @api.constrains('operation')
    def constrains_amount_operation(self):
        if self.amount > 0:
            if self.operation in ['D','-','NOTA DE DEBITO','CHEQUE']:
                self.amount = self.amount * -1

    @api.constrains('date_hour')
    def constrains_date_hour(self):
        self.date = str(self.date_hour)[:10]

    @api.constrains('date')
    def constrains_name(self):
        number = re.findall('\d+',self.name)
        name = ""
        for line in number:
            if name:
                name += ' '
            name += str(int(line))
        self.name = name
