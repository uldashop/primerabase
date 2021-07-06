# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrRecruitmentCompetition(models.Model):
    _name = 'hr.recruitment.competition'
    _description = ""

    name = fields.Char('Nombre')
    level_ids = fields.One2many('hr.recruitment.competition.level','competition_id','Nivel')
    departmet_ids = fields.Many2many('hr.department','hr_recruitment_competition_rel_department','competition_id','department_id',string="Departamento")
    job_ids = fields.Many2many('hr.job','hr_recruitment_competition_rel_job','competition_id','job_id',string="Puesto de Trabajo")
    general = fields.Boolean('General')
    company_id = fields.Many2one('res.company','Compañía', default=lambda self: self.env.company.id)
    active = fields.Boolean('Activo', default=True)

class hrRecruitmentCompetitionLevel(models.Model):
    _name = 'hr.recruitment.competition.level'
    _description = ""

    name = fields.Char('Nombre')
    level = fields.Char(string="Nivel")
    description = fields.Char('Descripcion')
    competition_id = fields.Many2one('hr.recruitment.competition','Competencia')
    department_ids = fields.Many2many('hr.department','competition_level_rel_department','level_id','department_id',string='Departamento')
    job_ids = fields.Many2many('hr.job','competition_level_rel_job','level_id','job_id',string='Puesto de Trabajo')
    company_id = fields.Many2one('res.company','Compañía', default=lambda self: self.env.company.id)

class hrDepartment(models.Model):
    _inherit = 'hr.department'

    competition_ids = fields.Many2many('hr.recruitment.competition','hr_recruitment_competition_rel_department','department_id','competition_id',string='Competencia')
    competition_level_ids = fields.Many2many('hr.recruitment.competition.level','competition_level_rel_department','department_id','level_id',string='Nivel de Competencia')

    @api.model
    @api.onchange('competition_ids','competition_level_ids','name')
    def update_competion(self):
        competition_ids = self.env['hr.recruitment.competition'].search([('company_id','=',self.company_id.id),('general','=',True)])
        for competition in competition_ids:
            if competition not in self.competition_ids:
                self.competition_ids = [(4,competition.id)]
        for level in self.competition_level_ids:
            if level.competition_id not in self.competition_ids:
                self.competition_ids = [(4,level.competition_id.id)]