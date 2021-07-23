# -*- coding: utf-8 -*-
# © 2014 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api,_

UPDATE_PARTNER_FIELDS = set([
    'firstname',
    'lastname',
    'user_id',
    'address_home_id'
])


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def split_name(self, name):
        clean_name = name.split(None, 1)
        return len(clean_name) > 1 and clean_name or (clean_name[0], False)

    def _auto_init(self):
        super(HrEmployee, self)._auto_init()
        self._update_employee_names()

    @api.model
    def _update_employee_names(self):
        employees = self.search([
            '|', ('firstname', '=', ' '), ('lastname', '=', ' ')])

        for ee in employees:
            lastname, firstname = self.split_name(ee.name)
            ee.write({
                'firstname': firstname,
                'lastname': lastname,
            })

    @api.model
    def _get_name(self, lastname, firstname):
        return ' '.join([lastname,firstname])

    @api.onchange('firstname', 'lastname')
    def get_name(self):
        if self.firstname and self.lastname:
            self.name = self._get_name(self.lastname, self.firstname)

    def _firstname_default(self):
        return ' ' if self.env.context.get('module') else False

    firstname = fields.Char(
        "Firstname", default=_firstname_default)
    lastname = fields.Char(
        "Lastname", required=True, default=_firstname_default)
    identification_id = fields.Char('Cédula')
    type_identifier = fields.Selection([('cedula', 'CEDULA'),('ruc', 'RUC'),
            ('pasaporte', 'PASAPORTE'),('nit', 'NIT')],'Tipo Identificación',required=True, default='cedula')

    @api.model
    def create(self, vals):
        if vals.get('firstname') and vals.get('lastname'):
            vals['name'] = self._get_name(vals['lastname'], vals['firstname'])

        elif vals.get('name'):
            ln, fn = self.split_name(vals['name'])
            vals['lastname'] = ln or ' '
            vals['firstname'] = fn or ' '
        res = super(HrEmployee, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('firstname') or vals.get('lastname'):
            lastname = vals.get('lastname') or self.lastname or ' '
            firstname = vals.get('firstname') or self.firstname or ' '
            vals['name'] = self._get_name(lastname, firstname)
        elif vals.get('name'):
            ln, fn = self.split_name(vals['name'])
            vals['lastname'] = ln
            vals['firstname'] = fn
        res = super(HrEmployee, self).write(vals)
        return res


    @api.constrains('identification_id')
    def create_partner(self):
        obj_partner = self.env['res.partner']
        partner_id = obj_partner.search([('identifier','=',self.identification_id)])
        if not partner_id:
            dct = {
                'company_type':'person',
                'type_identifier':self.type_identifier ,
                'identifier': self.identification_id,
                'mobile':self.mobile_phone,
                'phone':self.work_phone,
                'email':self.work_email,
                'country_id':self.country_id.id,
                'name': self.name,
                'company_id': self.env.company.id
            }
            partner = partner_id.create(dct)
            self.address_home_id = partner.id
        else:
            self.address_home_id = partner_id.id