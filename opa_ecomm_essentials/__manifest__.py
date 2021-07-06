# -*- coding: utf-8 -*-
{
    'name': " OPA Ecommerce Essentials",

    'summary': """
        Instalación de formulario con campos para Ecuador, adicionar campos de facturación a checkout""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Opa-Consulting - Guenael Labois, José García",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly alexander
    'depends': ['website', 'website_sale', 'website_sale_require_login'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/res.country.state.csv',
        'data/shipping.city.csv',
        'templates/assets.xml',
        'templates/payment.xml',
        'templates/register.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}
