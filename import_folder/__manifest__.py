# -*- coding: utf-8 -*-
{
    'name': "import_folder",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','stock_landed_costs','account','purchase','account_accountant'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/stock_landed_report_view.xml',
        'views/purchase_import_views.xml',
        'views/account_invoice_views.xml',
        # 'views/account_account_views.xml',
        'views/stock_landed_cost_views.xml',
        'views/account_payment_views.xml',
        'views/purchase_order_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
    ],
}