# -*- coding: utf-8 -*-
{
    'name': "OPA-Ecuador",

    'summary': """
        Localizacion Ecuatoriana OPA Consulting
        """,

    'description': """
        Localizacion Ecuatoriana OPA Consulting
    """,

    'author': "OPA Consulting",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Localization',
    'version': '1.2',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 
        'account',
        ],
    'demo': [
        'data/bootstrap.xml'
    ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/res.bank.csv',
        'data/account.payment.method.csv',
        'data/account.fiscal.position.csv',
        'data/account.tax.group.csv',
        'data/ats.country.csv',
        'data/ats.earning.csv',
        'data/account_type.xml',
        'data/group.xml',
        'data/account.xml',
        'data/tax.xml',
        'data/account.ats.sustento.csv',
        'data/account.ats.doc.csv',
        'data/partner.xml',
        'data/sequences.xml',
        'data/activity.limit.csv',
        'data/einvoice.xml',
        'data/account.epayment.csv',
        'view/authorisation_view.xml',
        'view/partner_view.xml',
        'view/actions.xml',
        'view/account_payment.xml',
        'view/report_disbursement.xml',
        'view/retention_view.xml',
        'view/edocument_layouts.xml',
        'view/report_einvoice.xml',
        'view/report_eretencion.xml',
        'view/report_ecreditnote.xml',
        'view/report_edebitnote.xml',
        'view/report_esettlementpurchase.xml',
        'view/account_tax_report.xml',
        'view/tax_views.xml',
        # 'view/res_company.xml',
        'edi/einvoice_edi.xml',
        'wizard/withholding_wizard.xml',

        #'data/bootstrap.xml'
    ],
    
}
