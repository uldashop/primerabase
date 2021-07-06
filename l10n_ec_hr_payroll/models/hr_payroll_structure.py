# -*- encoding: utf-8 -*-
from odoo import api, _, fields, models

class hrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        return [
            (0, 0, {
                "code":'ProvDec14',
                "name":'Provisión Decimo Cuarto',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_PROV"),
                "sequence":401,
                "appears_on_payslip":False,
                "condition_select":'python',
                "condition_python":'result = not employee.mensualize_14',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.WORK100.number_of_days
result = -(400.0/12.0/30 *days)''',
            }), 
            (0, 0, {
                "code":'ODESC',
                "name":'Otros Descuentos',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":309,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'fix',
                "quantity":1,
            }),
            (0, 0, {
                "code":'LOAN',
                "name":'Préstamos',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":308,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = inputs.LO and - (inputs.LO.amount)'
             }),
             (0, 0, {
                "code":'PROVFR',
                "name":'Provisión Fondo de Reserva',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_PROV"),
                "sequence":402,
                "appears_on_payslip":False,
                "condition_select":'python',
                "condition_python":'result = not employee.mensualize_fr and employee.has_13months(payslip.date_to, contract)',
                "amount_select":'code',
                "amount_python_compute":'''days = employee.has_13months(payslip.date_to, contract)
if days > 365:
    days = 30
result = (categories.APOR * 8.33 /100)/30 * days *-1'''
            }),
            (0, 0, {
                "code":'FR',
                "name":'Fondo de Reserva',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_NOAPOR"),
                "sequence":202,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.mensualize_fr and employee.has_13months(payslip.date_to, contract)',
                "amount_select":'code',
                "amount_python_compute":'''days = employee.has_13months(payslip.date_to, contract)
if days > 365:
    days = 30
result = (categories.APOR * 8.33 /100)/30 * days'''
            }),
            (0, 0, {
                "code":'ALIM',
                "name":'Alimentación',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":301,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = -(inputs.DALI and inputs.DALI.amount)'
            }),
            (0, 0, {
                "code":'NET',
                "name":'Salario a Recibir',
                "category_id": self.env.ref("hr_payroll.NET"),
                "sequence":1000,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = categories.APOR + categories.NAPOR + categories.DESC + IESSPER + categories.DED'
            }),
            (0, 0, {
                "code":'INGRESOS',
                "name":'Total Ingresos',
                "category_id": self.env.ref("hr_payroll.NET"),
                "sequence":250,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = categories.APOR + categories.NAPOR'
            }),
            (0, 0, {
                "code":'EGRESOS',
                "name":'Total Egresos',
                "category_id": self.env.ref("hr_payroll.NET"),
                "sequence":999,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = categories.DESC + IESSPER + categories.DED'
            }),
            (0, 0, {
                "code":'ABOQ',
                "name":'Abono Quincena',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "active":False,
                "sequence":310,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.has_payment(payslip.date_from)',
                "amount_select":'code',
                "amount_python_compute":'result = -((contract.wage * employee.porcentaje_sueldo) /100.0)'
            }),
            (0, 0, {
                "code":'MATERNIDAD',
                "name":'Maternidad',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":311,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'fix',
                "quantity":1,
                "amount_fix":0,
            }),
            (0, 0, {
                "code":'PENALI',
                "name":'Pensión Alimenticia',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":312,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = (inputs.PEN and inputs.PEN.amount) * -1'
            }),
            (0, 0, {
                "code":'UTIL',
                "name":'Utilidades',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_Benef"),
                "sequence":800,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'fix',
                "quantity":1,
                "amount_fix":0
            }),
            (0, 0, {
                "code":'DEC13',
                "name":'Décimo Tercero',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_NOAPOR"),
                "sequence":200,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.mensualize_13',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.WORK100.number_of_days
result = (categories.APOR/12.0)'''
            }),
            (0, 0, {
                "code":'IESSPER',
                "name":'Aporte IESS  Personal',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APTES"),
                "sequence":900,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = ((categories.APOR) * 9.45 / 100) * -1'
            }),
            (0, 0, {
                "code":'SUBIESS',
                "name":'Subsidios IESS',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":302,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = -(inputs.SUB and inputs.SUB.amount)'
            }),
            (0, 0, {
                "code":'IMPRENT',
                "name":'Impuesto a la Renta',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":303,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = -(employee.rent_tax)'
            }),
            (0, 0, {
                "code":'IESSPAT',
                "name":'Aporte IESS Patronal',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APTES"),
                "sequence":901,
                "appears_on_payslip":False,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = -(categories.APOR) * 12.15 / 100'
            }),
            (0, 0, {
                "code":'MOVIL',
                "name":'Movilización',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APOR"),
                "sequence":6,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = inputs.MOVI and inputs.MOVI.amount'
            }),
            (0, 0, {
                "code":'HSUPL',
                "name":'Horas Suplementarias',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APOR"),
                "sequence":3,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.supl_hour',
                "amount_select":'code',
                "amount_python_compute":'result = inputs.HSUP and inputs.HSUP.amount'
            }),
            (0, 0, {
                "code":'ProvDec13',
                "name":'Provisión Decimo Tercero',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_PROV"),
                "sequence":400,
                "appears_on_payslip":False,
                "condition_select":'python',
                "condition_python":'result = not employee.mensualize_13',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.WORK100.number_of_days
result = -(categories.APOR /12.0)'''
            }),
            (0, 0, {
                "code":'PRESQUI',
                "name":'Préstamos Quirografarios',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":304,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = (inputs.PQUIR and inputs.PQUIR.amount) * -1'
            }),
            (0, 0, {
                "code":'HEXTRA',
                "name":'Horas Extra',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APOR"),
                "sequence":2,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.extra_hour',
                "amount_select":'code',
                "amount_python_compute":'result = inputs.HEXT and inputs.HEXT.amount',
            }),
            (0, 0, {
                "code":'PRESHIP',
                "name":'Préstamos Hipotecarios',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":305,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = (inputs.PHIP and inputs.PHIP.amount) * -1'
            }),
            (0, 0, {
                "code":'MULTA',
                "name":'Multas',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":307,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = ((inputs.FAL and inputs.FAL.amount) + (inputs.ATRA and inputs.ATRA.amount)) * -1'
            }),
            (0, 0, {
                "code":'BONIF',
                "name":'Bonificaciones',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APOR"),
                "sequence":5,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = (inputs.BONIF and inputs.BONIF.amount)'
            }),
            (0, 0, {
                "code":'INDE',
                "name":'Indemnizacion',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_NOAPOR"),
                "sequence":5,
                "appears_on_payslip":False,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = (inputs.INDE and inputs.INDE.amount)'
            }),
            (0, 0, {
                "code":'SALARIO',
                "name":'Salario',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APOR"),
                "sequence":1,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = contract.wage'
            }),
            (0, 0, {
                "code":'COMISION',
                "name":'Comisiones',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_APOR"),
                "sequence":4,
                "appears_on_payslip":True,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'result = inputs.COMI and inputs.COMI.amount'
            }),
            (0, 0, {
                "code":'DEC14',
                "name":'Décimo Cuarto',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_NOAPOR"),
                "sequence":201,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.mensualize_14',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.WORK100.number_of_days
result = 400.0/12.0/30 *days'''
            }),
            (0, 0, {
                "code":'ANTP',
                "name":'Anticipos',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":306,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = employee.has_payment(payslip.date_from)',
                "amount_select":'code',
                "amount_python_compute":'result = -(employee.has_payment_amount(payslip.date_from,payslip.date_to))'
            }),
            (0, 0, {
                "code":'VACACIONES',
                "name":'Vacaciones',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_PROV"),
                "sequence":403,
                "appears_on_payslip":False,
                "condition_select":'none',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.WORK100.number_of_days
result = -(categories.APOR /24)'''
            }),
            (0, 0, {
                "code":'ProvBonDes',
                "name":'Provisión Bonificación por Desahucio',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_PROV"),
                "sequence":404,
                "appears_on_payslip":False,
                "condition_select":'none',
                "amount_select":'fix',
                "quantity":1,
            }),
            (0, 0, {
                "code":'ProvJubPat',
                "name":'Provisión Jubilación Patronal',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_PROV"),
                "sequence":405,
                "appears_on_payslip":False,
                "condition_select":'none',
                "amount_select":'fix',
                "quantity":1
            }),
            (0, 0, {
                "code":'Enfermedad',
                "name":'Ausencia por Enfermedad',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":301,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = worked_days.LEAVE110',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.LEAVE110.number_of_days
if days <=3:
    result = 0
else:
    result = worked_days.LEAVE110 and days * (contract.wage/30) * 0.75 * -1'''
            }),
            (0, 0, {
                "code":'VACATIONS',
                "name":'Vacaciones',
                "category_id": self.env.ref("l10n_ec_hr_payroll.rule_cat_DESC"),
                "sequence":301,
                "appears_on_payslip":True,
                "condition_select":'python',
                "condition_python":'result = worked_days.VACATION100',
                "amount_select":'code',
                "amount_python_compute":'''days = worked_days.VACATION100.number_of_days
result = worked_days.VACATION100 and days * (contract.wage/30) *-1'''
            })]

    rule_ids = fields.One2many('hr.salary.rule', 'struct_id',
        string='Salary Rules', default=_get_default_rule_ids)