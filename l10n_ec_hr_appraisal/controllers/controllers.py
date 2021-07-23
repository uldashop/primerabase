# -*- coding: utf-8 -*-
from odoo import http

# class L10nEcHrAppraisal(http.Controller):
#     @http.route('/l10n_ec_hr_appraisal/l10n_ec_hr_appraisal/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_ec_hr_appraisal/l10n_ec_hr_appraisal/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_ec_hr_appraisal.listing', {
#             'root': '/l10n_ec_hr_appraisal/l10n_ec_hr_appraisal',
#             'objects': http.request.env['l10n_ec_hr_appraisal.l10n_ec_hr_appraisal'].search([]),
#         })

#     @http.route('/l10n_ec_hr_appraisal/l10n_ec_hr_appraisal/objects/<model("l10n_ec_hr_appraisal.l10n_ec_hr_appraisal"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_ec_hr_appraisal.object', {
#             'object': obj
#         })