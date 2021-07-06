# -*- coding: utf-8 -*-
{
    'name': "Elearning Ecuador",

    'summary': """
        Se agregra control de fechas""",

    'description': """
        En este modulo se agregan las fechas de inicio y de fin de las capacitaciones.
    """,

    'author': "Opa Consulting",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_slides'],

    # always loaded
    'data': [
        "view/slide_channel_view.xml",
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
}