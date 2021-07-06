# -*- coding: utf-8 -*-
{
    'name': 'Employee Family',
    'version': '12.0.2.0.0',
    'summary': """Adding Advanced Fields In Employee Master""",
    'description': 'This module helps you to add more information in employee records.',
    'category': 'Generic Modules/Human Resources',
    'author': 'Kenneth Melgar',
    'company': 'Opa Consulting',
    'website': "https://www.opa-consulting.com",
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_view.xml',
    ],
    'demo': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
