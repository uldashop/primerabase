# -*- coding: utf-8 -*-
{
    'name': "Talent Growth",

    'summary': """
        Modulo de talent Growth""",

    'description': """
        En el presente modulo se llevara acabo el control de desarrollo y crecimiento del personal
    """,

    'author': "Opa Consulting",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Employee',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr'],

    # always loaded
    'data': [
        'security/hr_talent_growth_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_view.xml',
        'views/hr_talent_growth.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable':True,
    'application':True,
}