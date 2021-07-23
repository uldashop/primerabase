# -*- coding: utf-8 -*-
{
    'name': "Nomina Ecuador con Contabilidad",
    'summary': """
        Localizacion de Contabilidad de la Nomina""",
    'description': """
        En este modulo se agrega contabilidad de la nomina de localizacion Ecuatoriana
    """,
    'author': "Kenneth Melgar <kmelgar@opa-consulting.com>",
    'website': "http://www.opa-consulting.com",
    'category': 'Payroll Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_ec_hr_payroll','hr_payroll_account'],
    # always loaded
    'data': [
        'data/account.journal.csv',
        'views/res_config_settings.xml',
        'views/tenths_report.xml',
        'views/liquidation_settlement.xml',
        'views/hr_payslip_view.xml',
        'wizard/wizard_hr_fortnight.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
}