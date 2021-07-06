# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

from .utils import validar_identifier

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):

    _inherit = 'res.partner'

    def update_identifiers(self):
        sql = """UPDATE res_partner SET identifier='9999999999'
        WHERE identifier is NULL"""
        self.env.cr.execute(sql)

    def init(self):
        self.update_identifiers()
        super(ResPartner, self).init()
        #sql_index = """
        #CREATE UNIQUE INDEX IF NOT EXISTS
        #unique_company_partner_identifier_type on res_partner
        #(company_id, type_identifier, identifier)
        #WHERE type_identifier <> 'pasaporte'"""
        #self._cr.execute(sql_index)

    
    @api.depends('identifier', 'name')
    def name_get(self):
        data = []
        for partner in self:
            display_val = u'{0} {1}'.format(
                partner.identifier or '*',
                partner.name
            )
            data.append((partner.id, display_val))
        return data

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        if not args:
            args = []
        if name:
            partners = self.search([('identifier', operator, name)] + args, limit=limit)  # noqa
            if not partners:
                partners = self.search([('name', operator, name)] + args, limit=limit)  # noqa
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()

   
    @api.constrains('identifier', 'type_identifier')
    def _check_identifier(self):
        res = False
        res = validar_identifier(self.identifier, self.type_identifier)
        if not res:
            raise ValidationError('Error en el identificador.')
        partner_ids = self.env['res.partner'].search([('identifier','=',self.identifier),('id','!=',self.id),('company_id','=',self.company_id.id)])
        if partner_ids and self.identifier!='9999999999':
            raise ValidationError(_('Ya existe un contacto con esta identificacion.'))
        return True

   
    @api.depends('identifier')
    def _compute_tipo_persona(self):
        for s in self:
            if s.type_identifier == 'pasaporte':
                s.tipo_persona = '0'
            elif not s.identifier:
                s.tipo_persona = '0'
            elif int(s.identifier[2]) <= 6:
                s.tipo_persona = '6'
            elif int(s.identifier[2]) in [6, 9] and s.type_identifier=='ruc':
                s.tipo_persona = '9'
            else:
                s.tipo_persona = '0'

    ats_resident = fields.Selection([
        ('01', 'PAGO A RESIDENTE/ESTABLECIMIENTO PERMANENTE'),
        ('02', 'PAGO A NO RESIDENTE ')
    ], string="Tipo de pago", default='01')

    ats_country = fields.Many2one('ats.country', string='Pais')
    ats_country_efec_gen = fields.Many2one('ats.country', string='Pais Efec')
    ats_country_efec_parfic = fields.Many2one('ats.country', string='Pais Efec ParFis')

    ats_regimen_fiscal = fields.Selection([
        ('01', 'Regimen General'),
        ('02', 'Paraiso Fiscal'),
        ('03', 'Régimen fiscal preferente o jurisdicción de menor imposición')
    ], string='Regimen Fiscal', default='01')

    ats_doble_trib = fields.Boolean('Aplica doble tributacion', default=False)
    denopago = fields.Char('Denominacion', help='Denominación del régimen fiscal preferente o jurisdicción de menor imposición.')
    pag_ext_suj_ret_nor_leg = fields.Boolean('Sujeto a retencion', help='Pago al exterior sujeto a retención en aplicación a la norma legal', default=False)
    pago_reg_fis = fields.Boolean('Regimen Fiscal Preferente', help='El pago es a un régimen fiscal preferente o de menor imposición?', default=False)


    authorisation_ids = fields.One2many(
        'account.authorisation',
        'partner_id',
        'Autorizaciones'
        )

    identifier = fields.Char(
        'Cedula/ RUC',
        size=13,
        required=True,
        default='9999999999',
        help='Identificación o Registro Unico de Contribuyentes')

    type_identifier = fields.Selection(
        [
            ('cedula', 'CEDULA'),
            ('ruc', 'RUC'),
            ('pasaporte', 'PASAPORTE'),
            ('final', 'CONSUMIDOR FINAL'),
            ('nit', 'NIT')
        ],
        'Tipo ID',
        required=True,
        default='final'
    )

    tipo_persona = fields.Selection(
        compute='_compute_tipo_persona',
        selection=[
            ('6', 'Persona Natural'),
            ('9', 'Persona Juridica'),
            ('0', 'Otro')
        ],
        string='Persona',
        store=True
    )
    is_company = fields.Boolean(default=True)
    is_employee = fields.Boolean('Es Empleado', default=False)
    is_customs = fields.Boolean('Es Aduanas', default=False)

    #_sql_constraints = [('unique_identifier','unique(identifier)',u'El número de identificación es único.')]

    def get_authorisation(self, type_document):
        if type_document in ['entry','in_receipt', 'out_receipt']:
            return False
        map_type = {
            'out_invoice': '18',
            'in_invoice': '01',
            'sale_note': '02',
            'out_refund': '04',
            'in_refund': '04',
            'liq_purchase': '03',
            'ret_in_invoice': '07',
            'in_debit': '05',
            'out_debit': '05'
        }
        code = map_type[type_document]
        if self.is_customs and type_document == 'in_invoice':
            code = '16'
        candidates = [ a for a in self.authorisation_ids if a.active and a.type_id.code == code]
        
        if len(candidates):
            if code in ['18','04','07']:
                return candidates[0]
            else:
                return max(candidates,key=lambda x: x.num_start)

        return False


class ResCompany(models.Model):
    _inherit = 'res.company'

    withholding_agent = fields.Boolean(default=True, string='Withholding Agent')
    resolution_number = fields.Char('Resolution Number')
    accountant_id = fields.Many2one('res.partner', 'Contador')
    sri_id = fields.Many2one('res.partner', 'Servicio de Rentas Internas')
    cedula_rl = fields.Char('Cédula Representante Legal', size=10)
    contribuyente_especial = fields.Selection(
        [
            ('SI', 'SI'),
            ('NO', 'NO')
        ],
        string='Contribuyente Especial',
        required=True,
        default='NO'
    )
    electronic_signature = fields.Char(
        'Firma Electrónica',
        size=255,
    )
    password_electronic_signature = fields.Char(
        'Clave Firma Electrónica',
        size=255,
    )
    emission_code = fields.Selection(
        [
            ('1', 'Normal'),
            ('2', 'Indisponibilidad')
        ],
        string='Tipo de Emisión',
        required=True,
        default='1'
    )
    env_service = fields.Selection(
        [
            ('1', 'Pruebas'),
            ('2', 'Producción')
        ],
        string='Tipo de Ambiente',
        required=True,
        default='1'
    )
    agent_ids = fields.One2many('res.company.agent','company_id',string="Agentes")


class resPartnerBank(models.Model):
    _inherit = "res.partner.bank"


    account_type = fields.Selection([('savings', 'Savings Account'),
                                 ('checking', 'Checking Account')], string='Account Type')
    

class resCompanyAgent(models.Model):
    _name = "res.company.agent"
    _description = "Agentes de Retencion y Regimen"

    name = fields.Char(string="Nombre")
    description = fields.Char(string="Descripcion")
    company_id = fields.Many2one('res.company', string="Compañía")