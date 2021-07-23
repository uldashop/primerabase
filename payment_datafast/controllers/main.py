# -*- coding: utf-8 -*-

import json
import logging
import pprint

import requests
import werkzeug
from werkzeug import urls

from odoo import http
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)



class DatafastController(http.Controller):

    @http.route(['/payment/datafast/ressource'], type='http', auth='public')
    def datafast_ressource(self, **kwargs):

        #raise ValidationError(str(kwargs))
        res = kwargs['resourcePath']
        provider = http.request.env['payment.acquirer'].sudo().search([('provider', '=', 'datafast')])
        headers = {
            'Authorization': 'Bearer {}'.format(provider.datafast_token)
        }
        if provider.state == 'test':
            url = 'https://test.oppwa.com'
        else:
            url = 'https://oppwa.com'
        payment = requests.get('{}{}?entityId={}'.format(url, res, provider.datafast_entity_id), headers=headers)

        #raise ValidationError(str(payment.text))
        
        #if payment['result']['code'] in ['000.000.000', '000.100.112', '000.100.110']:

        request.env['payment.transaction'].sudo().form_feedback(payment, 'datafast')
        return werkzeug.utils.redirect('/payment/process')