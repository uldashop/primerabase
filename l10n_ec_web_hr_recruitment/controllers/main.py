# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.http import request
from werkzeug.exceptions import NotFound


class WebsiteHrRecruitment(http.Controller):

    @http.route('/jobs/add', type='http', auth="user", website=True)
    def jobs_add(self, **kwargs):
        job = request.env['hr.job'].with_context(rendering_bundle=True).create({
            'name': _('Job Title'),
            'description': _('Description'),
            'functions_ids': _('Functions'),
            'challenge_ids': _('Challenges'),
            'competition_ids': _('Competitions'),
        })
        return request.redirect("/jobs/detail/%s?enable_editor=1" % slug(job))

    @http.route('''/jobs/detail/<model("hr.job", "[('website_id', 'in', (False, current_website_id))]"):job>''', type='http', auth="public", website=True)
    def jobs_detail(self, job, **kwargs):
        if not job.can_access_from_current_website():
            raise NotFound()

        return request.render("website_hr_recruitment.detail", {
            'job': job,
            'main_object': job,
        })

    @http.route('''/jobs/apply/<model("hr.job", "[('website_id', 'in', (False, current_website_id))]"):job>''', type='http', auth="public", website=True)
    def jobs_apply(self, job, **kwargs):
        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
        if not job.can_access_from_current_website():
            raise NotFound()

        error = {}
        default = {}
        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')

        Study = env['hr.study']
        if job.study_ids:
            study_ids = job.study_ids.ids
        else:
            study_ids = Study.search([('active','=',True),('type_study','=','study')]).ids
        if job.further_training_ids:
            futher_ids = job.further_training_ids.ids
        else:
            futher_ids = Study.search([('active','=',True),('type_study','=','complementary')]).ids
        studies =Study.sudo().browse(study_ids)
        training = Study.sudo().browse(futher_ids)

        return request.render("l10n_ec_web_hr_recruitment.apply", {
            'job': job,
            'error': error,
            'default': default,
            'studies':studies,
            'training': training,
        })
