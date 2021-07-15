# -*- coding: utf-8 -*-
{
    'name': "Web Ulda",

    'summary': """Web de Ulda""",

    'description': """
        Web de Ulda
    """,

    'author': "Opa Consulting",
    'website': "https://www.opa-consulting.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','website', 'theme_clarico_vega'],

    # always loaded
    'data': [
        'templates/assets.xml',
        'templates/header.xml',
        'templates/footer.xml',
        'templates/shop.xml',
        'templates/web_pages_snnipets.xml',
        # 'templates/dev.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
