# -*- coding: utf-8 -*-

from odoo import api,fields, models, _
from ast import literal_eval
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    struct_id = fields.Many2one('hr.payroll.structure', string='Estructura Salarial',company_dependent=True)
    journal_payroll = fields.Many2one('account.journal', string='Nomina',company_dependent=True)
    journal_payroll_pay = fields.Many2one('account.account', string='Cuenta de Pago Nomina',company_dependent=True)
    journal_fortnight = fields.Many2one('account.journal', string='Anticipo',company_dependent=True)
    journal_fortnight_pay = fields.Many2one('account.account', string='Cuenta de Pago Anticipo',company_dependent=True)
    journal_xiii = fields.Many2one('account.account', string='Cuenta de Decimo Tercer Sueldo',company_dependent=True)
    journal_xiv = fields.Many2one('account.account', string='Cuenta de Decimo Cuarto Sueldo',company_dependent=True)
    journal_vacation = fields.Many2one('account.account', string='Cuenta de Vacaciones', company_dependent=True)
    journal_settlement = fields.Many2one('account.account', string='Cuenta de Finiquito',company_dependent=True)
    journal_payslip = fields.Many2one('account.journal', string='Diario de Pagos',company_dependent=True)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.default'].sudo()
        struct_id = ICPSudo.get("res.config.settings",'struct_id',False,self.env.company.id)
        journal_payroll = ICPSudo.get("res.config.settings",'journal_payroll',False,self.env.company.id)
        journal_payroll_pay = ICPSudo.get("res.config.settings",'journal_payroll_pay',False,self.env.company.id)
        journal_fortnight = ICPSudo.get("res.config.settings",'journal_fortnight',False,self.env.company.id)
        journal_fortnight_pay = ICPSudo.get("res.config.settings",'journal_fortnight_pay',False,self.env.company.id)
        journal_xiii = ICPSudo.get("res.config.settings",'journal_xiii',False,self.env.company.id)
        journal_xiv = ICPSudo.get("res.config.settings",'journal_xiv',False,self.env.company.id)
        journal_vacation = ICPSudo.get("res.config.settings",'journal_vacation',False,self.env.company.id)
        journal_settlement = ICPSudo.get("res.config.settings",'journal_settlement',False,self.env.company.id)
        journal_payslip = ICPSudo.get("res.config.settings",'journal_payslip',False,self.env.company.id)

        res.update(
            struct_id=struct_id, 
            journal_payroll=journal_payroll,
            journal_payroll_pay=journal_payroll_pay,
            journal_fortnight=journal_fortnight,
            journal_fortnight_pay=journal_fortnight_pay,
            journal_xiii=journal_xiii,
            journal_xiv=journal_xiv,
            journal_vacation=journal_vacation,
            journal_settlement=journal_settlement,
            journal_payslip=journal_payslip,
            )
        return res


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.default'].sudo()
        ICPSudo.set("res.config.settings",'struct_id',self.struct_id.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_payroll',self.journal_payroll.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_payroll_pay',self.journal_payroll_pay.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_fortnight',self.journal_fortnight.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_fortnight_pay',self.journal_fortnight_pay.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_xiii',self.journal_xiii.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_xiv',self.journal_xiv.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_vacation',self.journal_vacation.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_settlement',self.journal_settlement.id,False,self.env.company.id)
        ICPSudo.set("res.config.settings",'journal_payslip',self.journal_payslip.id,False,self.env.company.id)
