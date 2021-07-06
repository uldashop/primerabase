# -*- coding: utf-8 -*-
{
    'name': "RRHH Proceso de Seleccion",

    'summary': """
        Se agregran Competencias y niveles""",

    'description': """
        En este modulo se agregan competencias y sus diferentes niveles en el proceso de 
        seleccion para que mediante estas se pueda evaluar al personal.
    """,

    'author': "Opa Consulting",
    'website': "http://www.opa-consulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Employee',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_recruitment'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "security/website_hr_recruitment_security.xml",
        "views/recruitment_competition_view.xml",
        "views/hr_department_view.xml",
        "views/hr_job_view.xml",
        "views/hr_employee_view.xml",
        "views/menuitem_view.xml",
        "data/hr_competition_data.xml",
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
}