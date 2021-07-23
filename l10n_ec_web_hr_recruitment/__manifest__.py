# -*- coding: utf-8 -*-
{
    'name': "Sitio Web RRHH Proceso de Seleccion",

    'summary': """
        Crea Diseño de website para puestos de trabajo""",

    'description': """
        Crea Diseño de website, usando informacion en el sistema
        para publicacion de puestos de trabajo""",

    'author': "Opa Consulting",
    'website': "https://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Employee',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_ec_hr_recruitment','website_hr_recruitment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/template_web_hr_recruitment.xml',
    ],
    'demo': [],
    'installable':True,
}