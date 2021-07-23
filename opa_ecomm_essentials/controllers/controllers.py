# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound
import werkzeug
import random
import string
from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv import expression
import math
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.l10n_ec.models.utils import validar_identifier
_logger = logging.getLogger(__name__)

def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

class WebsiteSaleInherit(WebsiteSale):

    def _get_mandatory_billing_fields(self):
        base = ["name", "email", "street", "city_id", "country_id", "identifier", "type_identifier"]
        return base

    def _get_mandatory_shipping_fields(self):
        return ["name", "street", "city_id", "country_id"]

    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True, sitemap=False)
    def address(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order()
        State = request.env['res.country.state'].sudo()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        mode = (False, False)
        can_edit_vat = False
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))
        if partner_id == -1 and kw.get('identifier'):
            partner_id  = Partner.sudo().search([('identifier','=', kw.get('identifier')),('type_identifier','=', kw.get('type_identifier'))]).id or -1
        #     kw['partner_id'] = partner_id

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            can_edit_vat = True
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                    can_edit_vat = order.partner_id.can_edit_vat()
                else:
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
                #names = values['name'].split('  ')
                #if len(names) == 2:
                #    values['name'] = names[0] 
                #    values['last_name'] = names[1]
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else: # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._checkout_form_save(mode, post, kw)
                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.with_context(not_self_saleperson=True).onchange_partner_id()
                    # This is the *only* thing that the front end user will see/edit anyway when choosing billing address
                    order.partner_invoice_id = partner_id
                    if not kw.get('use_same'):
                        kw['callback'] = kw.get('callback') or \
                            (not order.only_services and (mode[0] == 'edit' and '/shop/checkout' or '/shop/address'))
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
                if not errors:
                    return request.redirect(kw.get('callback') or '/shop/confirm_order')

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id
        # def_state_id = State.search([('code','=','468',),('country_id','=', country.id)])
        state = 'state_id' in values and values['state_id'] != '' and request.env['res.country.state'].browse(int(values['state_id']))
        state = state and state.exists() or None
        fiscal_position = request.env['account.fiscal.position'].sudo().search([])
        identification = [{'id':'cedula','name':'Cédula'},
                        {'id':'ruc','name':'RUC'},{'id':'pasaporte','name':'Pasaporte'}]
        fiscal = Partner.browse(partner_id).property_account_position_id.id if Partner.browse(partner_id) and Partner.browse(partner_id).property_account_position_id else ''
        dom = []
        
        city_id = 'city_id' in values and values['city_id'] != '' and request.env['shipping.city'].browse(int(values['city_id']))
        city_id = city_id and city_id.exists() or []
        if city_id:
            dom = [('city_id','=',city_id.id)]
        render_values = {
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'can_edit_vat': can_edit_vat,
            'country': country,
            'countries': country.search([('name','=','Ecuador')]),
            'states': country.get_website_sale_states(mode=mode[1]),
            'state': state,
            'city_id': city_id, 
            'cities': state.get_website_sale_city(mode=mode[1]) if state else [],
            'error': errors,
            'callback': kw.get('callback'),
            'only_services': order and order.only_services,
            'fiscal_positions':fiscal_position,
            'fiscal_position_id':fiscal,
            'identification':identification,
        }
        
        return request.render("website_sale.address", render_values)

    def values_postprocess(self, order, mode, values, errors, error_msg):
        new_values = {}
        authorized_fields = request.env['ir.model'].sudo().search([('model', '=', 'res.partner')])._get_form_writable_fields()
        for k, v in values.items():
            # don't drop empty value, it could be a field to reset
            if k in authorized_fields and v is not None:
                new_values[k] = v
            else:  # DEBUG ONLY
                if k not in ('field_required', 'partner_id', 'callback', 'submitted'): # classic case
                    _logger.debug("website_sale postprocess: %s value has been dropped (empty or not writable)" % k)
        default_id = '9999999999'
        new_values['name'] = values['name'] #+ '  ' + values['last_name']
        new_values['type_identifier'] = values['type_identifier']
        new_values['identifier'] = values['identifier'] if 'identifier' in values else default_id
        new_values['city_id'] = values['city_id']

        
        new_values['property_account_position_id'] = int(values['property_account_position_id']) if 'property_account_position_id' in values else ''
        #new_values['customer'] = True
        new_values['team_id'] = request.website.salesteam_id and request.website.salesteam_id.id

        if mode[0] == 'new':
            new_values['company_id'] = request.website.company_id.id

        lang = request.lang if request.lang in request.website.mapped('language_ids.code') else None
        if lang:
            new_values['lang'] = lang
        if mode == ('edit', 'billing') and order.partner_id.type == 'contact':
            new_values['type'] = 'other'
        if mode[1] == 'shipping':
            new_values['parent_id'] = order.partner_id.commercial_partner_id.id
            new_values['type'] = 'delivery'

        return new_values, errors, error_msg


    def checkout_form_validate(self, mode, all_form_values, data):
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []

        # Required fields from form
        required_fields = [f for f in (all_form_values.get('field_required') or '').split(',') if f]
        # Required fields from mandatory field function
        required_fields += mode[1] == 'shipping' and self._get_mandatory_shipping_fields() or self._get_mandatory_billing_fields()
        # Check if state required
        country = request.env['res.country']
        if data.get('country_id'):
            country = country.browse(int(data.get('country_id')))
            if 'state_code' in country.get_address_fields() and country.state_ids:
                required_fields += ['state_id']

        # error message for empty required fields
        for field_name in required_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # phone validation
        if not data.get('phone').isdigit():
            error["phone"] = 'error'
            error_message.append(_('Número de teléfono inválido. Solo puede contener dígitos.'))
        
        if len(data.get('phone')) < 7:
            error["phone"] = 'error'
            error_message.append(_('Número de teléfono inválido. Minimo 7 dígitos.'))

        if len(data.get('street')) < 6:
            error["street"] = 'error'
            error_message.append(_('Direccion invalida.'))

        
        # vat validation
        validate = validar_identifier(data.get("identifier"),data.get("type_identifier"))
        #raise Exception(validate)
        #idenficacion = 'cédula' if data.get("type_identifier") == 'cedula' else 'RUC'
        if data.get('type_identifier')=='cedula':
            idenficacion = 'Cédula'
        elif data.get('type_identifier') == 'ruc':
            idenficacion = 'RUC'
        else:
            idenficacion = 'Pasaporte'

        if not validate and data.get("type_identifier") != 'pasaporte':
            error["identifier"] = 'error'
            error_message.append(_('La identificación %s es inválida.' % (idenficacion)))
        
        partner = request.env.user.partner_id
        existing = request.env['res.partner'].sudo().search([('type_identifier', '=', data.get('type_identifier')), ('identifier', '=', data.get('identifier'))])
        
        if len(existing) > 0:
            if existing[0].id != partner.id:
                error["identifier"] = 'error'
                error_message.append(_('La identificación %s ya esta registrada.' % (idenficacion)))

        
        Partner = request.env['res.partner']
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if data.get("country_id"):
                data["vat"] = Partner.fix_eu_vat_number(data.get("country_id"), data.get("vat"))
            partner_dummy = Partner.new({
                'vat': data['vat'],
                'country_id': (int(data['country_id'])
                               if data.get('country_id') else False),
            })
            try:
                partner_dummy.check_vat()
            except ValidationError:
                error["vat"] = 'error'

        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message

    def _checkout_form_save(self, mode, checkout, all_values):
        Partner = request.env['res.partner']
        partner_id = ''
        if checkout['identifier'] != '9999999999':
            partner_id = Partner.sudo().search([('identifier','=',checkout['identifier']),('type_identifier','=',checkout['type_identifier'])])
        if mode[0] == 'new' and not partner_id:
            partner_id = Partner.sudo().create(checkout).id
        elif mode[0] == 'edit' or partner_id:
            if partner_id:
                partner_id = partner_id.id
            partner_id = partner_id or int(all_values.get('partner_id', 0))
            if partner_id > 0:
                # double check
                order = request.website.sale_get_order()
                shippings = Partner.sudo().search([("id", "child_of", order.partner_id.commercial_partner_id.ids)])
                # if partner_id not in shippings.mapped('id') and partner_id != order.partner_id.id:
                #     return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
            else:
                partner_id = Partner.sudo().create(checkout).id
        return partner_id


    @http.route(['/shop/state_infos/<model("res.country.state"):state>'], type='json', auth="public", methods=['POST'], website=True)
    def state_infos(self, state, mode, **kw):
        return dict(
            city_id=[(st.id, st.name) for st in state.get_website_sale_city(mode=mode)],
        )

    @http.route(['/shop/city/<phrase>'], type='http', auth="public", methods=['GET'], website=False)
    def institution_infos2(self, phrase, **kw):
        inst = request.env['shipping.city'].search([
            ('name', 'ilike', phrase),
        ])
        resp = [{ 'name': st.name, 'id': st.id} for st in inst]
        
        return json.dumps(resp)

class PortalInherit(CustomerPortal):

    MANDATORY_BILLING_FIELDS = ["name", "phone", "email", "street", "city_id", "country_id"]
    OPTIONAL_BILLING_FIELDS = ["zipcode", "state_id", "vat", "company_name", "type_identifier", 'identifier', 'phone_extension']

    @http.route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })

        if post and request.httprequest.method == 'POST':
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in self.MANDATORY_BILLING_FIELDS}
                values.update({key: post[key] for key in self.OPTIONAL_BILLING_FIELDS if key in post})
                for field in set(['country_id', 'state_id','city_id']) & set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except:
                        values[field] = False
                values.update({'zip': values.pop('zipcode', '')})
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        cities = request.env['shipping.city'].sudo().search([])
        identification = [{'id':'cedula','name':'Cédula'},
                        {'id':'ruc','name':'RUC'},{'id':'pasaporte','name':'Pasaporte'}]
        values.update({
            'partner': partner,
            'countries': countries,
            'states': states,
            'cities': cities,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'redirect': redirect,
            'page_name': 'my_details',
            'identification': identification
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    def details_form_validate(self, data):
        error = dict()
        error_message = []

        # Validation
        for field_name in self.MANDATORY_BILLING_FIELDS:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        
        partner = request.env.user.partner_id
        validate = validar_identifier(data.get("identifier"),data.get("type_identifier"))
        #raise Exception(validate)

        #idenficacion = 'cédula' if data.get("type_identifier") == 'cedula' else 'RUC'
        if data.get('type_identifier')=='cedula':
            idenficacion = 'Cédula'
        elif data.get('type_identifier') == 'ruc':
            idenficacion = 'RUC'
        else:
            idenficacion = 'Pasaporte'

        if not validate and data.get("type_identifier") != 'pasaporte':
            error["identifier"] = 'error'
            error_message.append(_('La identificación %s es inválida.' % (idenficacion)))
        
        partner = request.env.user.partner_id
        existing = request.env['res.partner'].sudo().search([('type_identifier', '=', data.get('type_identifier')), ('identifier', '=', data.get('identifier'))])
        
        if len(existing) > 0:
            if existing[0].id != partner.id:
                error["identifier"] = 'error'
                error_message.append(_('La identificación %s ya esta registrada.' % (idenficacion)))
            
        if not data.get('phone').isdigit():
            error["phone"] = 'error'
            error_message.append(_('Número de teléfono inválido. Solo puede contener dígitos.'))

        if len(data.get('phone')) < 7:
            error["phone"] = 'error'
            error_message.append(_('Número de teléfono inválido. Mínimo 7 dígitos.'))

        if len(data.get('street')) < 6:
            error["street"] = 'error'
            error_message.append(_('Dirección inválida.'))

        
        # vat validation
        if data.get("vat") and partner and partner.vat != data.get("vat"):
            if partner.can_edit_vat():
                if hasattr(partner, "check_vat"):
                    if data.get("country_id"):
                        data["vat"] = request.env["res.partner"].fix_eu_vat_number(int(data.get("country_id")), data.get("vat"))
                    partner_dummy = partner.new({
                        'vat': data['vat'],
                        'country_id': (int(data['country_id'])
                                       if data.get('country_id') else False),
                    })
                    try:
                        partner_dummy.check_vat()
                    except ValidationError:
                        error["vat"] = 'error'
            else:
                error_message.append(_('Changing VAT number is not allowed once document(s) have been issued for your account. Please contact us directly for this operation.'))

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        unknown = [k for k in data if k not in self.MANDATORY_BILLING_FIELDS + self.OPTIONAL_BILLING_FIELDS]
        if unknown:
            error['common'] = 'Unknown field'
            error_message.append("Unknown field '%s'" % ','.join(unknown))

        return error, error_message

class Signup(AuthSignupHome):

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                # Send an account creation confirmation email
                if qcontext.get('token'):
                    User = request.env['res.users']
                    user_sudo = User.sudo().search(
                        User._get_login_domain(qcontext.get('login')), order=User._get_login_order(), limit=1
                    )
                    template = request.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False)
                    if user_sudo and template:
                        template.sudo().with_context(
                            lang=user_sudo.lang,
                            auth_login=werkzeug.url_encode({'auth_login': user_sudo.email}),
                        ).send_mail(user_sudo.id, force_send=True)
                return self.web_login(*args, **kw)
            except UserError as e:
                qcontext['error'] = e.name or e.value
            except (SignupError, AssertionError) as e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _("Another user is already registered using this email address.")
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _("Could not create a new account.")

        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    def get_auth_signup_qcontext(self):
        """ Shared helper returning the rendering context for signup and reset password """
        qcontext = request.params.copy()
        #if 'name' in qcontext:
        #    qcontext['name'] = '  '.join([qcontext.get('name'), qcontext.get('surname')])
        qcontext.update(self.get_auth_signup_config())
        if not qcontext.get('token') and request.session.get('auth_signup_token'):
            qcontext['token'] = request.session.get('auth_signup_token')
        if qcontext.get('token'):
            try:
                # retrieve the user info (name, login or email) corresponding to a signup token
                token_infos = request.env['res.partner'].sudo().signup_retrieve_info(qcontext.get('token'))
                for k, v in token_infos.items():
                    qcontext.setdefault(k, v)
            except:
                qcontext['error'] = _("Invalid signup token")
                qcontext['invalid_token'] = True
        qcontext["providers"] = self.list_providers()
        return qcontext

