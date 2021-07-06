from odoo import models, fields, api

from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)

class Activity(models.Model):
    _name = 'activity.limit'
    rec_name = 'name'

    activity = fields.Char('Actividad')
    category = fields.Char('Category')
    amount = fields.Float('Limite')
    name = fields.Char('Nombre', compute="_get_name")

   
    def _get_name(self):
        for record in self:
            record.name = "%s - %s" % (record.activity, record.category)

   
    def name_get(self):
        result = []
        for record in self:
            name = "%s - %s" % (record.activity, record.category)
            result.append((record.id, name))
        return result
