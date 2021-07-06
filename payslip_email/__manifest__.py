{
    'name': "payslip_email",
    'summary': """payslip_email""",
    'description': """Payslip Email""",
    'author': "OPA-Consulting",
    'website': "http://www.opa-consulting.com",
    'category': 'Debug',
    'version': '13.0.1',
    'depends': ['base','hr_payroll'],
    'data': [
        'views/hr_payslip_views.xml',
        'data/template_mail_rol.xml',
    ],
    'auto_install': True,
}