# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, _, api

# class HrEmployeeContractName(models.Model):
#     """This class is to add emergency contact table"""

#     _name = 'hr.emergency.contact'
#     _description = 'HR Emergency Contact'

#     number = fields.Char(string='Numero', help='Numero de Contacto')
#     relation = fields.Char(string='Contacto', help='Relacion con empleado')
#     employee_obj = fields.Many2one('hr.employee', invisible=1)


class HrEmployeeFamilyInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.family'
    _description = 'HR Employee Family'

    def mail_reminder(self):
        """Sending expiry date notification for Job Permit"""

        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match1 = self.search([])
        for i in match1:
            if i.visa_expire:
                exp_date1 = fields.Date.from_string(i.visa_expire) - timedelta(days=180)
                if date_now >= exp_date1:
                    mail_content = "  Hello  " + i.name + ",<br>Your Job Permit " + i.permit_no + "is going to expire on " + \
                                   str(i.visa_expire) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Job Permit-%s Expired On %s') % (i.permit_no, i.visa_expire),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

    member_name = fields.Char(string='Nombre')
    employee_ref = fields.Many2one(string="Is Employee",
                                   help='If family member currently is an employee of same company, '
                                        'then please tick this field',
                                   comodel_name='hr.employee')
    employee_id = fields.Many2one(string="Employee", help='Select corresponding Employee', comodel_name='hr.employee',
                                  invisible=1)
    relation = fields.Selection([('father', 'Padre'),
                                 ('mother', 'Madre'),
                                 ('daughter', 'Hija'),
                                 ('son', 'Hijo'),
                                 ('wife', 'Cónyuge/Pareja')], string='Relacion', help='Relacion con empleado')
    member_contact = fields.Char(string='Contact No')
    fecha_relevante = fields.Date('Fecha de Nacimiento/Matrimonio', default = False)
    discapacidad = fields.Boolean('Tiene Discapacidad', default = False)
    porc_discapacidad = fields.Float('Porcentaje discapacidad')
    years = fields.Integer('Años', compute="_compute_years")

    @api.depends('fecha_relevante')
    def _compute_years(self):
        for s in self:
            s.years = int((date.today() - s.fecha_relevante).days / 365.25) if date.today() > s.fecha_relevante else 0


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    fam_ids = fields.One2many('hr.employee.family', 'employee_id', string='Family', help='Family Information')
    # certificate_id = fields.Many2one('hr.certificate', string="Education Level")
    certificate = fields.Selection([('master','Master'),
                                    ('third_level','Third Level'),
                                    ('bachelor','Bachiller'),
                                    ('primary','Primary'),
                                    ('other','Other')])

# class hrCertificate(models.Model):
#     _name = "hr.certificate"
#     _description = "Education Level"

#     name = fields.Char(string="Education Level")