# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date

class hrJobPosition(models.Model):
    _inherit = 'hr.job'

    competition_ids = fields.Many2many('hr.recruitment.competition','hr_recruitment_competition_rel_job','job_id','competition_id',string='Competencia')
    competition_level_ids = fields.Many2many('hr.recruitment.competition.level','competition_level_rel_job','job_id','level_id',string='Nivel de Competencia')

    mission = fields.Text(string='Job Mission')
    challenge_ids = fields.Many2many('hr.job.challenge','hr_job_rel_challenge','job_id','challenge_id',string='Challenge or Dare')
    decision_ids = fields.Many2many('hr.job.decision','hr_job_rel_decision','job_id','decision_id',string='Decisions to Consult')
    wage = fields.Integer(string="Wage")
    wage_to = fields.Integer(string="Wage")
    study_ids = fields.Many2many('hr.study','hr_job_rel_study','job_id','study_id', string='Academic Preparation')
    further_training_ids = fields.Many2many('hr.study','hr_job_rel_training','job_id','training_id', string='Further Training')
    experience = fields.Char(string="Work Experience")
    lang_ids = fields.Many2many('res.lang','hr_job_rel_lang','job_id','lang_id',string="Language")
    function_ids = fields.Many2many('hr.job.function','hr_job_rel_function','job_id','function_id','Function')
    relation = fields.Text(string='Internal/External Relation')
    equipment_ids = fields.Many2many('hr.job.equipment','hr_job_rel_equipment','job_id','equipment_id', string="Job Equipment")
    physical_condition_ids = fields.Many2many('hr.physical.condition','hr_job_rel_physical_condition','job_id','physical_condition_id', string="Physical Condition")
    rick_ids = fields.Many2many('hr.rick.factor','hr_job_rel_rick','job_id','rick_id', string="Rick Factor's")
    protective_ids = fields.Many2many('hr.job.equipment','hr_job_rel_equipment_protective','job_id','protective_id', string="Protective Equipment")
    history_ids = fields.One2many('hr.job.history', 'job_id', string="Selection History")
    date_end = fields.Date(string='End Date')

    @api.model
    @api.onchange('competition_ids','competition_level_ids','name','department_id')
    def update_competion(self):
        competition_ids = self.env['hr.recruitment.competition'].search([('company_id','=',self.company_id.id),('general','=',True)])
        for competition in competition_ids:
            if competition not in self.competition_ids:
                self.competition_ids = [(4,competition.id)]
        for level in self.competition_level_ids:
            if level.competition_id not in self.competition_ids:
                self.competition_ids = [(4,level.competition_id.id)]
        for department in self.department_id.competition_ids:
            if department not in self.competition_ids:
                self.competition_ids = [(4,department.id)]

    
    def set_recruit(self):
        super(hrJobPosition,self).set_recruit()
        if not self.date_end:
            raise UserError(_('Primero ingrese la fecha de finalizacion.'))
        dtc = {'date_start':date.today(),
                'date_planned': self.date_end,
                'job_id': self.id}
        self.history_ids.create(dtc)

    def set_open(self):
        super(hrJobPosition,self).set_open()
        for history in self.history_ids:
            if not history.date_end:
                history.date_end = date.today() 
        self.date_end = ''


class hrJobChallenge(models.Model):
    _name = 'hr.job.challenge'
    _description = "Challenge of Job"

    name = fields.Char(string='Challenge')
    job_ids = fields.Many2many('hr.job','hr_job_rel_challenge','challenge_id','job_id','Job Position')
    active = fields.Boolean(string="Active", default=True)


class hrJobDecision(models.Model):
    _name = 'hr.job.decision'
    _description = "Decisions of Job"

    name = fields.Char(string='Name')
    job_ids = fields.Many2many('hr.job','hr_job_rel_decision','decision_id','job_id','Job Position')
    active = fields.Boolean(string="Active", default=True)


class hrJobEquipment(models.Model):
    _name = 'hr.job.equipment'
    _description = "Job Equipment"

    name = fields.Char(string='Equipment')
    job_ids = fields.Many2many('hr.job','hr_job_rel_equipment','equipment_id','job_id','Job Position')
    type_equipment = fields.Selection([('general','General'),
                                        ('protective','Protective')], string="Type", default="general")
    active = fields.Boolean(string="Active", default=True)


class hrJobFunction(models.Model):
    _name = 'hr.job.function'
    _description = "Functions"

    name = fields.Char(string='Function Name')
    type_periodicity = fields.Selection([('hour','Hour(s)'),
                                        ('day','Day(s)'),
                                        ('week','Week(s)'),
                                        ('month','Month(s)'),
                                        ('year','Year(s)')],string="Type Periodicity", default="month")
    periodicity = fields.Integer(string="Periodicity")
    job_ids = fields.Many2many('hr.job','hr_job_rel_function','function_id','job_id','Job Position')
    active = fields.Boolean(string="Active", default=True)


class resLang(models.Model):
    _inherit = 'res.lang'

    job_ids = fields.Many2many('hr.job','hr_job_rel_lang','lang_id','job_id',string="Job Position")


class study(models.Model):
    _name = 'hr.study'
    _description = 'Studies'

    name = fields.Char(string="Study Name")
    job_ids = fields.Many2many('hr.job','hr_job_rel_study','study_id','job_id', string='Job Position')
    type_study = fields.Selection([('study', 'Academic Preparation'),
                                   ('complementary', 'Further Training')],string="Type", default="study")
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class physicalCondition(models.Model):
    _name = 'hr.physical.condition'
    _description = 'Physical Condition'

    name = fields.Char(string="Physical Condition")
    job_ids = fields.Many2many('hr.job','hr_job_rel_physical_condition','physical_condition_id','job_id', string='Job Position')
    active = fields.Boolean(string="Active", default=True)


class rickFactor(models.Model):
    _name = 'hr.rick.factor'
    _description = "Rick Fator's"

    name = fields.Char(string="Rick Name")
    job_ids = fields.Many2many('hr.job','hr_job_rel_rick','rick_id','job_id', string='Job Position')
    active = fields.Boolean(string="Active", default=True)


class jobHistory(models.Model):
    _name = 'hr.job.history'
    _description = 'Selection History'
    _rec_name = 'date_start'

    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    date_planned = fields.Date(string="Expected End Date")
    job_id = fields.Many2one('hr.job', string="Job Position")