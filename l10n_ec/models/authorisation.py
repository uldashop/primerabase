# -*- coding: utf-8 -*-
 

import time
from datetime import datetime, date

from odoo import api, fields, models
from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)


class AccountAuthorisation(models.Model):

    _name = 'account.authorisation'
    _order = 'expiration_date desc'
    _rec_name = 'display_name'

    @api.depends('type_id', 'num_start', 'num_end', 'is_electronic', 'serie_emision', 'serie_entidad')   
    def _display_name(self):
        for s in self:
            name = u'[%s-%s del %s al %s] %s' % (
                s.serie_entidad,
                s.serie_emision,
                s.num_start,
                s.num_end or 'EL',
                s.type_id.name
            )
            s.display_name = name

    
    @api.depends('expiration_date', 'is_electronic')
    def _compute_active(self):
        """
        Check the due_date to give the value active field
        """
        for s in self:
            if s.is_electronic:
                s.active = True
                return
            if not s.expiration_date:
                return
            now = date.today()
            due_date = s.expiration_date #datetime.strptime(s.expiration_date, '%Y-%m-%d')
            s.active = now < due_date

    def _get_type(self):
        return self._context.get('type', 'in_invoice')  # pylint: disable=E1101

    def _get_in_type(self):
        return self._context.get('in_type', 'externo')

    def _get_type_code(self):
        code = self._context.get('default_type_code', None)
        if code:
            type_obj=self.env['account.ats.doc']
            return type_obj.search([('code', '=', code)], limit=1)
        return None

    def _get_partner(self):
        partner = self.env.company.partner_id
        if self._context.get('partner_id'):
            partner = self._context.get('partner_id')
        return partner

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, values):
        res = self.search([('partner_id', '=', values['partner_id']),
                           ('type_id', '=', values['type_id']),
                           ('serie_entidad', '=', values['serie_entidad']),
                           ('serie_emision', '=', values['serie_emision']),
                           ('active', '=', True),
                           ('is_electronic', '=', values['is_electronic'])
                           ])
                           
        if res and res.in_type=='interno':
            MSG = u'Ya existe una autorización activa para %s' % self.type_id.name  # noqa
            raise ValidationError(MSG)

        partner_id = self.env.company.partner_id.id
        if values['partner_id'] == partner_id:
            typ = self.env['account.ats.doc'].browse(values['type_id'])
            name_type = '{0}_{1}_{2}_{3}'.format(values['name'] or 'electronic', values['type_id'], values['serie_entidad'], values['serie_emision'])
            sequence_data = {
                'code': typ.code == '07' and 'account.retention' or 'account.move',  # noqa
                'name': name_type,
                'padding': 9,
                'number_next': values['num_start'],
                }
            seq = self.env['ir.sequence'].create(sequence_data)
            values.update({'sequence_id': seq.id})
        return super(AccountAuthorisation, self).create(values)

   
    def unlink(self):
        inv = self.env['account.move']
        res = inv.search([('auth_inv_id', '=', self.id)])
        if res:
            raise UserError(
                'Esta autorización esta relacionada a un documento.'
            )
        return super(AccountAuthorisation, self).unlink()

    name = fields.Char('Num. de Autorización', size=128)
    display_name = fields.Char('Display name', compute="_display_name", store=True)
    serie_entidad = fields.Char('Serie Entidad', size=3, required=True)
    serie_emision = fields.Char('Serie Emision', size=3, required=True)
    num_start = fields.Integer('Desde', default=1)
    num_end = fields.Integer('Hasta')
    is_electronic = fields.Boolean('Documento Electrónico ?')
    electronic_installed = fields.Boolean('Module electronico instalado', compute="_get_electronic_invoice")
    expiration_date = fields.Date('Fecha de Vencimiento')
    active = fields.Boolean(
        string='Activo',
        default=True
        )
    in_type = fields.Selection(
        [('interno', 'Internas'),
         ('externo', 'Externas')],
        string='Tipo Interno',
        readonly=True,
        change_default=True,
        default=_get_in_type
        )
    type_id = fields.Many2one(
        'account.ats.doc',
        'Tipo de Comprobante',
        required=True,
        default=_get_type_code
        )
    partner_id = fields.Many2one(
        'res.partner',
        'Empresa',
        required=True,
        default=_get_partner
        )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Secuencia',
        help='Secuencia Alfanumerica para el documento, se debe registrar cuando pertenece a la compañia',  # noqa
        ondelete='cascade'
        )

    _sql_constraints = [
        ('number_unique',
         'unique(partner_id,name,serie_emision,serie_entidad,expiration_date,type_id,is_electronic)',
         u'La relación de autorización, serie entidad, serie emisor y tipo, debe ser única.'),  # noqa
        ]

    def is_valid_number(self, number):
        """
        Metodo que verifica si @number esta en el rango
        de [@num_start,@num_end]
        """
        if self.type_id.code not in ['01', '02', '03', '04', '05', '06', '07', '08', '18']:
            return True
        if self.is_electronic and self.num_start <= int(number) :
            return True
        if self.num_start <= int(number) <= self.num_end:
            return True
        return False


    @api.onchange('name','is_electronic')
    def onchange_name(self):
        if self.name:
            if not self.is_electronic and len(self.name) != 10:
                raise UserError('La numeración ingresada no coincide con el formato del SRI de 10 digitos.')
            elif self.is_electronic and len(self.name) != 37:
                raise UserError('La numeración ingresada no coincide con el formato del SRI de 37 digitos.')

    @api.depends('active', 'is_electronic', 'name')   
    def _get_electronic_invoice(self):
        self.electronic_installed = True
    



