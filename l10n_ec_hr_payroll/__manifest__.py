# -*- coding: utf-8 -*-
{
    'name': "Nomina Ecuador",
    'summary': """
        Localizacion de Nomina""",
    'description': """
        En este modulo se agregan reglas salariales, Motivos de Despidos, etc.
    """,
    'author': "Kenneth Melgar <kmelgar@opa-consulting.com>",
    'website': "http://www.opa-consulting.com",
    'category': 'Payroll Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_payroll','l10n_ec','l10n_ec_hr_employee'],
    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "data/hr.income.tax.csv",
        "data/hr.personal.expenses.limit.csv",
        "data/hr.contract.type.csv",
        "data/hr.work.entry.type.csv",
        "data/hr.leave.type.csv",
        "data/salary_rule_category.xml",
        "data/salary_rule.xml",
        "data/hr_payslip_input_type.xml",
        "data/settlement_type.xml",
        "data/iess_sectorial_commission.xml",
        "data/iess_sectorial_branch.xml",
        "data/iess_sectorial_job.xml",
        "views/hr_employee_view.xml",
        "views/hr_contract_view.xml",
        "views/hr_income_tax.xml",
        "views/hr_personal_expenses.xml",
        "views/hr_iess_sectorial.xml",
        "views/hr_payslip_view.xml",
        "views/hr_fortnight_view.xml",
        "reports/report_payslip.xml",
        "reports/tenths_report.xml",
        "reports/income_tax_report.xml",
        "reports/settlement_report.xml",
        "reports/vacation_report.xml",
        "wizard/tenths_report_view.xml",
        "wizard/wizard_rdep.xml",
        "wizard/wizard_income_tax_view.xml",
        "wizard/settlement_report_view.xml",
        "wizard/wizard_fortnight_view.xml",
        "wizard/vacation_report.xml",
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
}