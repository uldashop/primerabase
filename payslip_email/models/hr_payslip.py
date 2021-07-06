from odoo import fields, models, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def generate_massive_template(self):
        for employee in self:
            getattr(employee, "message_post")(
                subtype='mt_comment',
                body="Rol enviado",
            )
            tmpl = self.env.ref("payslip_email.email_template_rol")
            tmpl.send_mail(
                employee.id, force_send=True
            )
        message = "Correo Enviado exitosamente"
        return {
            'name': 'Registros',
            'type': 'ir.actions.act_window',
            'res_model': 'message.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_message': message
            }
        }

class message_wizard(models.TransientModel):
    _name = 'message.wizard'
    _description = 'Message wizard'

    message = fields.Text(string="Message", readonly=True, store=True)