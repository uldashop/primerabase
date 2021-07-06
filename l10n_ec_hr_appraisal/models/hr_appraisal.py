# -*- coding: utf-8 -*-

from odoo import models, fields, api

class hrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    competition =  fields.Boolean('Incluir Competencias')
    format_matriz = fields.Boolean('Obtener Matriz')

    def send_appraisal(self):
        ComposeMessage = self.env['survey.mail.compose.message']
        for appraisal in self:
            appraisal_receiver = appraisal._prepare_user_input_receivers()
            for survey, receivers in appraisal_receiver:
                for employee in receivers:
                    email = employee.related_partner_id.email or employee.work_email
                    if not email:
                        continue
                    render_template = appraisal.mail_template_id.with_context(email=email, survey=survey, employee=employee).generate_email([appraisal.id])
                    values = {
                        'survey_id': survey.id,
                        'public': 'email_private',
                        'partner_ids': employee.related_partner_id and [(4, employee.related_partner_id.id)] or False,
                        'multi_email': email,
                        'subject': '%s appraisal: %s' % (appraisal.employee_id.name, survey.title),
                        'body': render_template[appraisal.id]['body'],
                        'date_deadline': appraisal.date_close,
                        'model': appraisal._name,
                        'res_id': appraisal.id,
                    }
                    compose_message_wizard = ComposeMessage.with_context(active_id=appraisal.id, active_model=appraisal._name, notif_layout="mail.mail_notification_light").create(values)
                    compose_message_wizard.send_mail()  # Sends a mail and creates a survey.user_input
                    if employee.user_id:
                        user_input = survey.user_input_ids.filtered(
                            lambda user_input: user_input.partner_id == employee.user_id.partner_id and user_input.appraisal_id == appraisal and user_input.state != 'done'
                        )
                        if user_input:
                            form_url = survey.public_url + '/' + user_input[0].token
                        else:
                            form_url = survey.public_url
                        appraisal.activity_schedule(
                            'hr_appraisal.mail_act_appraisal_form', appraisal.date_close,
                            note=_('Fill form <a href="%s">%s</a> for <a href="#" data-oe-model="%s" data-oe-id="%s">%s\'s</a> appraisal') % (
                                form_url, survey.display_name,
                                appraisal.employee_id._name, appraisal.employee_id.id, appraisal.employee_id.display_name),
                            user_id=employee.user_id.id)
            appraisal.message_post(body=_("Appraisal form(s) have been sent"))
        return True

