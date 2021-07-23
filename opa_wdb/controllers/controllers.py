# -*- coding: utf-8 -*-
# from odoo import http


# class Addons/tools(http.Controller):
#     @http.route('/addons/tools/addons/tools/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/addons/tools/addons/tools/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('addons/tools.listing', {
#             'root': '/addons/tools/addons/tools',
#             'objects': http.request.env['addons/tools.addons/tools'].search([]),
#         })

#     @http.route('/addons/tools/addons/tools/objects/<model("addons/tools.addons/tools"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('addons/tools.object', {
#             'object': obj
#         })
