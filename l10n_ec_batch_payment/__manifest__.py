# -*- coding: utf-8 -*-
{
    'name': "Lotes de pago Ecuador",

    'summary': """
        Transferencias Bancarias en Lotes
        """,

    'description': """
        Se agregar exportacion de documento de tranferecia bancaria en lotes para localizacion Ecuador
    """,

    'author': "Kenneth Melgar<kenneth.melgarf@ug.edu.ec>",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    'version': '1.2',

    # any module necessary for this one to work correctly
    'depends': [
        'account_batch_payment'
        ],
    'demo': [
    ],
    # always loaded
    'data': [
        'view/account_batch_payment_view.xml',
    ],
    
}
