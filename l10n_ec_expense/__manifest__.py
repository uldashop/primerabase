# -*- coding: utf-8 -*-
{
    'name': "Localizacion de Gastos Personales",

    'summary': """
        Ajustes por localizacion """,

    'description': """
        Se permite generar gastos personales por compañia
    """,

    'author': "Opa Consulting",
    'website': "http://www.opa-cosulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_expense'],

    # always loaded
    'data': [
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable':True,
}