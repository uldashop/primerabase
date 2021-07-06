# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Stock Report',
    'version': '1.0',
    'category': 'Stock/Inventory',
    'summary': 'Inventory',
    'description': """
With this application, you can manage the zones and routes from the sales configuration
===========================================================================
 """,
    'author': "Nelio Ciguenia",
    'website': 'https://odoo.opa-consulting.com/',
    'depends': ['base_setup',
                'account_reports',
                'account',
                ],
    'data': [
        'wizards/report_inventory_views.xml',
        'wizards/report_inventario_month_views.xml',
        'security/ir.model.access.csv',
            ],
    # 'demo': ['data/sales_team_demo.xml'],
    'installable': True,
    'auto_install': False,
}

