# -*- coding: utf-8 -*-
from odoo import api,fields,models, _
from datetime import date
from odoo.exceptions import ValidationError, UserError

class settlementType(models.Model):
    _name = 'hr.settlement.type'
    _description = _('Settlement Type')

    name =  fields.Char('Description')
    code = fields.Char('Code')
    active = fields.Boolean(default=True)


class hrContract(models.Model):
    _inherit = 'hr.contract'

    sectoral_id = fields.Many2one('iess.sectorial.job', string="Job Iess")
    salary = fields.Float('Reference Salary', related="sectoral_id.value", readonly=True)
    struct_id = fields.Many2one('hr.payroll.structure', string="Payroll Structure")
    contract_history_ids = fields.One2many('hr.contract.history','contract_id',string='Historial de Salario')
    contract_type_id = fields.Many2one('hr.contract.type',string='Tipo de Contrato')

    @api.constrains('state','employee_id','company_id')
    def constrains_employee_state(self):
        contract_ids = self.env['hr.contract'].search([
            ('employee_id','=',self.employee_id.id),
            ('state','=','open'),
            ('id','!=',self.id),
            ('company_id','=',self.company_id.id)],
            limit=1

        )
        if self.state == 'open' and contract_ids:
            raise ValidationError(_('An employee cannot have more than one active contract.'))

    @api.constrains('wage')
    def constrains_wage(self):
        data = []
        history_obj = self.env['hr.contract.history']
        history = history_obj.search([('contract_id','=',self.id)], order='id desc', limit=1)
        if history and history.wage > self.wage:
            raise ValidationError(_("No se puede cambiar salario a monto inferior al actual."))
        user = self.env['res.users'].browse(self._uid)
        data.append((0,0,{
                'wage':self.wage,
                'date':date.today(),
                'user': user.name,
                'contract_id':self.id,
        }))
        self.contract_history_ids = data


class hrContractHistory(models.Model):
    _name = 'hr.contract.history'
    _description = 'Contract History'
    _rec_name = 'wage'

    wage = fields.Float(string='Salario')
    date = fields.Date(string='Fecha de Cambio')
    user = fields.Char(string='Usuario')
    contract_id = fields.Many2one('hr.contract',string='Contrato')

class hrContractType(models.Model):
    _name = 'hr.contract.type'
    _description = 'Contract Type'

    name = fields.Char('Name')