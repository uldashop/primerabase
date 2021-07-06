# -*- coding: utf-8 -*-
{
    'name': "Evaluacion y Encuestas",

    'summary': """
        Agrupa funcionalidades de Evaluacion y Encuestas con Puestos de Trabajo""",

    'description': """
        A partir de los puestos de Trabajo se elaboran Encuestas que seran utilizadas dentro de
        las evaluacion si asi el usuario lo desea, esta encuesta se basa en las competencias 
        que cada puesto de trabajo tenga, para asi tambien tener un control dentro de los puestos
        de trabajo.
    """,

    'author': "Opa Consulting",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Employee',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_ec_hr_recruitment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_job_view.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable':True,
}