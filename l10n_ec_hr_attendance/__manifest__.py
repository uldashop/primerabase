# -*- coding: utf-8 -*-
{
    'name': "Asistencias Ec.",

    'summary': """
        Importacion de biometrico Ecuatoriano""",

    'description': """
        Este modulo se encarga de ajustar el modulo de asistencias con la localizacion Ecuatoriana
    """,

    'author': """Kenneth Melgar<kenneth.melgarf@ug.edu.ec>,
                 Opa Consulting""",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Employee',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_attendance','l10n_ec_hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance_view.xml',
        'views/res_config_settings_view.xml',
        'wizard/wizard_hr_attendance_view.xml',
    ],
    'installable': True,
}