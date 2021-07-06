# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta


class importFolder(models.Model):
    _name = 'import.folder'
    _inherit = ['mail.thread','mail.activity.mixin']


    import_folder = fields.Boolean("Carpeta de Importaciones", default=lambda self: self.env.user.company_id.po_double_validation == 'two_step')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id.id
    )
    import_folder_father = fields.Boolean("Tiene carpeta padre", default=False)
    import_id = fields.Many2one('import.folder', 'Carpeta padre')

    name = fields.Char('Nombre')
    elaboration_date =  fields.Date('Fecha desde', required=True, default=fields.Date.today())
    responsable = fields.Many2one('res.users', 'Responsable',default=lambda self: self.env.user.id)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('open', 'Abierto'),
        ('close', 'Terminado')], string='Estado', index=True, readonly=True, default='draft')  

    type_import = fields.Char('Tipo')
    bl = fields.Char('B/L #')
    container = fields.Char('Contenedor') 
    dai = fields.Char('DAI #')
    warehouse = fields.Char('Almacen')
    customs_regime = fields.Char('Regimen Aduana')
    boarding_date = fields.Date('Fecha de Embarque')
    estimated_date = fields.Date('Fecha de Arribo Estimada')
    arrival_date = fields.Date('Fecha de Llegada a Puerto')
    arrival_days = fields.Integer('Tiempo de Llegada a Ecuador dias')
    admission_date = fields.Date('Fecha de Ingreso a Bodega')
    processing_time = fields.Integer('Tiempo de Tramite Aduanero')
    cellar = fields.Char('Bodega a la que Ingresa') 
   
    #=======Lineas======#
    invoice_ids = fields.One2many( 'account.move',
                                    'import_ids',
                                    )
   
    stock_ids = fields.One2many(   'stock.picking',
                                    'import_ids')
   
    stock_landed_ids = fields.One2many('stock.landed.cost',
                                            'import_ids')
   
    payment_ids = fields.One2many( 'account.payment',
                                    'import_ids')
                                    
    purchase_ids = fields.One2many('purchase.order',
                                    'import_ids')






