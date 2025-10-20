# -*- coding: utf-8 -*-
# from odoo import http


# class EimsIntegration(http.Controller):
#     @http.route('/eims_integration/eims_integration', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/eims_integration/eims_integration/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('eims_integration.listing', {
#             'root': '/eims_integration/eims_integration',
#             'objects': http.request.env['eims_integration.eims_integration'].search([]),
#         })

#     @http.route('/eims_integration/eims_integration/objects/<model("eims_integration.eims_integration"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('eims_integration.object', {
#             'object': obj
#         })

