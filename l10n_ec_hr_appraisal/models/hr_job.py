# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class hrJob(models.Model):
    _inherit = 'hr.job'

    survey_id = fields.Many2one('survey.survey', 'survey_id')

    def create_survey(self):
        if not self.competition_ids:
            raise ValidationError(_('No tiene competencias para poder crear la encuesta'))

        survey_obj = self.env['survey.survey']
        level_competition_ids = self.env['hr.recruitment.competition.level'].search([('company_id','=',self.company_id.id),
                            ('competition_id','in',self.competition_ids._ids)])
        if not self.survey_id:
            question_and_page_ids = []
            question_ids = []
            sequence=1

            question_and_page_ids.append((0,0,{
                'title': _('COMPETENCIAS'),
                'is_page':True,
                'sequence':sequence
            }))

            for competition in self.competition_ids:
                value_ids = []
                for level in level_competition_ids:
                    if competition.id == level.competition_id.id:
                        value_ids.append((0,0,{
                            'value':level.level,
                        }))
                if value_ids != []:
                    sequence+=1
                    question_and_page_ids.append((0,0,{
                                                    'title':competition.name,
                                                    'constr_mandatory':True,
                                                    'is_page':False,
                                                    'question_type':'simple_choice',
                                                    'sequence':sequence,
                                                    'labels_ids': value_ids,
                                                }))
            
            survey = {
                'title': _('Evaluacion de Competencias de %s' %(self.name)),
                'users_can_go_back':True,
                'auth_required':True,
                'quizz_mode':True,
                'question_and_page_ids':question_and_page_ids,
                'stage_id':1,
            }
            survey_id = survey_obj.create(survey) 
            self.survey_id = survey_id.id
