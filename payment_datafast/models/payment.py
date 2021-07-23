# coding: utf-8

import json
import logging
import requests

import dateutil.parser
import pytz
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare, float_round
from odoo.http import request

import base64


_logger = logging.getLogger(__name__)

STAGING_URL = "https://test.oppwa.com/v1"
PROD_URL = "https://oppwa.com/v1"

class AcquirerDatafast(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('datafast', 'Datafast')])
    datafast_mid = fields.Char('Merchant Id')
    datafast_tid = fields.Char('Terminal Id')
    datafast_entity_id = fields.Char('Entity Id')
    datafast_token = fields.Char('Token')
    datafast_phase1 = fields.Boolean('Fase 1')
    datafast_checkout_id = fields.Char('checkout_id')
    datafast_tax_group_iva0_id = fields.Many2one('account.tax.group', 'Groupo de Impuesto Iva 0%')
    datafast_tax_group_iva12_id = fields.Many2one('account.tax.group', 'Groupo de Impuesto Iva 12%')


    #@api.onchange('datafast_phase1')
    #def onchangeState(self):
    #    if self.datafast_phase1:
    #        self.datafast_entity_id = "8a829418533cf31d01533d06f2ee06fa"
    #        self.datafast_token = "OGE4Mjk0MTg1MzNjZjMxZDAxNTMzZDA2ZmQwNDA3NDh8WHQ3RjIyUUVOWA=="
    #        self.state = 'test'
            
    def datafast_form_generate_values(self, tx_values):
        
        # Datafast needs access to cart data
        sale_order = tx_values['reference'].split('-')[0]

        cart = self.env['sale.order'].search([('name', '=', sale_order)])
        new_data = {
            'cart': cart,
        }
        tx_values.update(new_data)
        checkout = self._get_checkout_id(self._get_datafast_url_base(),tx_values)
        #raise ValidationError(str(checkout.text))
        if checkout.status_code == 200:
            self.datafast_checkout_id = checkout.json()['id']
        else:
            raise ValidationError('No se pudo crear el checkout con datafast.{}'.format(str(checkout.text)))
        tx_values['checkout_id'] = self.datafast_checkout_id
        tx_values['mode'] = self.state
        return tx_values


    def datafast_get_form_action_url(self):
        pass
    
    def _get_datafast_url_base(self):
        if self.state == 'test':
            return STAGING_URL
        else:
            return PROD_URL

    def _get_checkout_id(self,url,tx_values):
        #raise ValidationError(str(tx_values['cart'].amount_by_group))
        headers = {
            'Authorization': 'Bearer {}'.format(self.datafast_token)
        }
        if self.datafast_phase1:
            payload = {
                'entityId': self.datafast_entity_id,
                'amount': '{:.2f}'.format(tx_values['amount']),
                'currency': tx_values['currency'].name,
                'paymentType': 'DB' 
            }
        else:
            ip_address = request.httprequest.environ['REMOTE_ADDR']
            merch_id = '_'.join([self.datafast_mid, self.datafast_tid])
            iva0 = baseIva0 = iva12 = baseIva12 = 0.0
            tax0_str = self.datafast_tax_group_iva0_id.name
            tax12_str = self.datafast_tax_group_iva12_id.name
            
            for tax in tx_values['cart'].amount_by_group:
                if tax[0] == tax0_str:
                    iva0 = float_round(tax[1], precision_digits=2)
                    baseIva0 = float_round(tax[2], precision_digits=2)
                if tax[0] == tax12_str:
                    iva12 = float_round(tax[1], precision_digits=2)
                    baseIva12 = float_round(tax[2], precision_digits=2)
            payload = {
                'entityId': self.datafast_entity_id,
                'amount': '{:.2f}'.format(tx_values['amount']),
                'currency': tx_values['currency'].name,
                'paymentType': 'DB',
                'customer.givenName': tx_values['partner'].name,
                #'customer.middleName': 'N/A',
                'customer.surname': tx_values['partner'].name,
                'customer.ip': ip_address,
                'customer.email': tx_values['partner'].email,
                'customer.merchantCustomerId': tx_values['partner'].id,
                'customer.identificationDocType': 'IDCARD',
                'customer.identificationDocId': '{:0>10s}'.format(tx_values['partner'].identifier[:10]),
                'merchantTransactionId': 'trx_{}'.format(tx_values['reference']),
                'customer.phone': tx_values['partner'].phone,
                'shipping.country': tx_values['partner'].country_id.code,
                'billing.country': tx_values['billing_partner_country'].code,
                'billing.street1': tx_values['billing_partner_address'][:100],
                'shipping.street1': tx_values['billing_partner_address'][:100],
                'risk.parameters[USER_DATA2]':'Dermashop',
                'customParameters[{}]'.format(merch_id): '00810030070103910004012{:0>12d}05100817913101052012{:0>12d}053012{:0>12d}'.format(int(iva12*100), int(baseIva0*100), int(round(baseIva12*100)))

            }
            
            cart_count=0
            for line in tx_values['cart'].order_line:
                payload.update({
                    'cart.items[{}].name'.format(cart_count): line.name[:255],
                    'cart.items[{}].description'.format(cart_count): line.name[:255],
                    'cart.items[{}].price'.format(cart_count): '{:.2f}'.format(float_round(line.price_unit * (1 - (line.discount or 0.0) /100),precision_digits=2)),
                    'cart.items[{}].quantity'.format(cart_count): line.product_uom_qty,
                })
                cart_count+=1
            if self.state == 'test':
                payload.update({
                    'testMode': 'EXTERNAL'
                })
            #raise Exception('baseIva12 = {}|{}'.format(baseIva12,str(payload)))
        return requests.post('{}/checkouts'.format(url), data=payload, headers=headers)

class TxDatafast(models.Model):
    _inherit = 'payment.transaction'

    datafast_data = fields.Binary('Resultado de transaction')
    datafast_filename = fields.Char('Archivo de transaccion')
    datafast_bin = fields.Char('Bin')
    datafast_lot = fields.Char('Lote')
    datafast_card_type = fields.Char('Tipo de tarjeta')
    datafast_auth = fields.Char('Authorizacion')


    def _datafast_form_get_tx_from_data(self, data):
        b64data = base64.b64encode(data.text.encode())
        filename = data.json()['id']+'.txt'
        try:
            datafast_bin = data.json()['card']['bin']
            datafast_lot = data.json()['resultDetails']['ReferenceNbr']
            datafast_card_type = data.json()['paymentBrand']
            datafast_auth = data.json()['resultDetails']['AuthCode']
        except:
            datafast_bin = 'error Tx'
            datafast_lot = 'error Tx'
            datafast_card_type = 'error Tx'
            datafast_auth = 'error Tx'


        reference = data.json()['merchantTransactionId'][4:]
        tx = self.env['payment.transaction'].search([('reference','=',reference)])

        if data.json()['result']['code'] in ['000.000.000','000.100.112','000.100.110']:
            tx._set_transaction_done()
            
        else:
            try:
                tx._set_transaction_error(data.json()['resultDetails']['ExtendedDescription'] or 'Error desconocido')
            except:
                tx._set_transaction_error(data.json())
        tx.write({
            'datafast_data': b64data,
            'datafast_filename': filename,
            'datafast_bin': datafast_bin,
            'datafast_auth': datafast_auth,
            'datafast_lot': datafast_lot,
            'datafast_card_type': datafast_card_type
        })
        return tx

    