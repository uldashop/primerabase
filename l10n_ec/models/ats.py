# -*- coding: utf-8 -*-
 

import time
from datetime import datetime, date

from odoo import api, fields, models
from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)

class AccountAtsDoc(models.Model):
    _name = 'account.ats.doc'
    _description = 'Tipos Comprobantes Autorizados'

    code = fields.Char('Código', size=2, required=True)
    name = fields.Char('Tipo Comprobante', size=64, required=True)


class AccountAtsSustento(models.Model):
    _name = 'account.ats.sustento'
    _description = 'Sustento del Comprobante'

   
    @api.depends('code', 'type')
    def name_get(self):
        res = []
        for record in self:
            name = '%s - %s' % (record.code, record.type)
            res.append((record.id, name))
        return res

    _rec_name = 'type'

    code = fields.Char('Código', size=2, required=True)
    type = fields.Char('Tipo de Sustento', size=128, required=True)


class AtsCountry(models.Model):
    _name = 'ats.country'
    
    name = fields.Char('Nombre')
    code = fields.Char('Code')
    is_fiscal_paradise = fields.Boolean("Paraiso Fiscal")



class AtsEarning(models.Model):
    _name = 'ats.earning'

    name = fields.Char('Nombre')
    code = fields.Char('Code')