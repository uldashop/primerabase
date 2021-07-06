# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta
from odoo.addons import decimal_precision as dp
import json
import xlsxwriter
from io import BytesIO
import base64
import string  
from collections import Counter

class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    valuation_adjustment_lines = fields.One2many(
        'stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
        states={'done': [('readonly', True)]})

    def get_additional_landed_cost(self,product_id,quantity):
        lis=[]
        tit=[]
        for i in self.valuation_adjustment_lines:
            if i.product_id.id == product_id and i.quantity == quantity:
                dct={
                    'additional_landed_cost':i.additional_landed_cost,
                    }
                lis.append(dct)
                tit.append(i.cost_line_id.name)
        return lis,tit

    def product_info(self):
        lis=[]
        control=[]                
        for i in self.valuation_adjustment_lines:
            if i.product_id.id not in control or i.quantity not in control:
                control.append(i.product_id.id)
                control.append(i.quantity)
                cos,cant = self.get_additional_landed_cost(i.product_id.id,i.quantity)
                dct={
                    'pro_name':i.product_id.name,
                    'add':lis,
                    'weight':i.weight,
                    'volume':i.volume,
                    'quantity':i.quantity,
                    'measurement':i.product_id.product_tmpl_id.uom_id.name,
                    'cost':cos,
                    'former_cost_per_unit':i.former_cost/i.quantity,
                    'former_cost':i.former_cost,
                    }
                lis.append(dct)           
        return lis, cant

    def fix_date(self,date):
        return date.strftime("%m/%d/%Y")

    def import_info(self):
        lis=[]
        for i in self.import_ids:
            lis=[{'name':'TIPO', 'value':i.type_import},
                {'name':'B/L #', 'value':i.bl},
                {'name':'CONTENEDOR', 'value':i.container},
                {'name':'DAI #', 'value':i.dai},
                {'name':'ALMACEN', 'value':i.warehouse},
                {'name':'REGIMEN ADUANA', 'value':i.customs_regime},
                {'name':'FECHA DE EMBARQUE', 'value':self.fix_date(i.boarding_date) or ''},
                {'name':'FECHA DE ARRIBO ESTIMADA', 'value':self.fix_date(i.boarding_date) or ''},
                {'name':'FECHA DE LLEGADA A PUERTO', 'value':self.fix_date(i.arrival_date) or ''},
                {'name':'TIEMPO DE LLEGADA A ECUADOR DIAS', 'value':i.arrival_days},
                {'name':'FECHA DE INGRESO A BODEGA', 'value':self.fix_date(i.admission_date) or ''},
                {'name':'TIEMPO DE TRAMITE ADUANERO', 'value':i.processing_time},
                {'name':'BODEGA A LA QUE INGRESA', 'value':i.cellar}]
        return lis
           
   
    def report(self):
        file_data =  BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        import_info=self.import_info()
        product, tit= self.product_info()      
        name = 'Reporte de Gastos de Envio'
        self.xslx_body(workbook,product,tit,name,import_info)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': name,
            'store_fname': name,
            'type': 'binary',
            #'datas_fname': name+'.xlsx',
        })
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += "/web/content/%s?download=true" %(attachment.id)
        return{
        "type": "ir.actions.act_url",
        "url": url,
        "target": "new",
        }

    def xslx_body(self,workbook,product,tit,name,import_info):       
        title = workbook.add_format({'bold':True,'border':1})
        title.set_center_across()
        currency_format = workbook.add_format({'num_format': '[$$-409]#,##0.00','border':1 })
        sub_currency_format = workbook.add_format({'num_format': '[$$-409]#,##0.00','border':1,'bold':True})
        body_right = workbook.add_format({'align': 'right', 'border':1 })
        body_left = workbook.add_format({'align': 'left', 'border':1 })
        body = workbook.add_format({'align': 'left', 'border':0 })
        sheet = workbook.add_worksheet(name)
        sheet.merge_range('E2:H2', name.upper(), title)
        letter=list(string.ascii_uppercase)  
        colspan = 1
        col = 2        
        lis_tit=('Producto','Peso','Volumen','Cantidad','Unidad de medida','Coste anterior (por unidad)','Coste anterior')
        tit_f=('COSTO FINAL DE PRODUCTO (POR UNIDAD)','COSTE NUEVO')
        join=lis_tit+tuple(tit)+tit_f
        for imp in import_info:
            col+=1
            if col == 10:
                col = 3
                colspan+=4
            sheet.write(col,colspan,imp['name'],body)
            sheet.write(col,colspan+2,imp['value'],body)
        col=col+3
        colspan = 1
        colspan1= 1
        c=0
        col1=col
        for j in join:
            sheet.set_column('{0}:{0}'.format(chr(c + ord('B'))), len(j) + 4)
            c+=1
            sheet.write(col,colspan1,j,title)
            colspan1+=1
            if c==25:
                c=-1
                sheet.set_column('A{0}:{0}'.format(chr(c + ord('B'))), len(j) + 4)
                c += 1
        
        sheet.set_column('B:B', 80)
        sheet.set_column('F:F', 20)
        for p in product:
            col+=1
            var=0
            sheet.write(col,colspan,p['pro_name'],body_left)
            sheet.write(col+1,colspan,'Total',title)
            sheet.write(col,colspan+1,p['weight'],body_right)
            sheet.write(col,colspan+2,p['volume'],body_right)
            sheet.write(col,colspan+3,p['quantity'],body_right)
            sheet.write(col,colspan+4,p['measurement'],body_right)
            sheet.write(col,colspan+5,p['former_cost_per_unit'],currency_format)
            sheet.write(col,colspan+6,p['former_cost'],currency_format)
            form='=sum('+letter[colspan+6]+str(col+1)+':'+letter[colspan+6]+str(col1+2)+')'
            sheet.write(col+1,colspan+6,form,sub_currency_format)

            colspan1=colspan
            colspan2=0
            for i in p['cost']:   
                sheet.write(col,colspan1+7,i['additional_landed_cost'],currency_format)
                if colspan1+7>25:
                    form1='=sum(A'+letter[colspan2]+str(col+1)+':A'+letter[colspan2]+str(col1+2)+')'
                    colspan2+=1
                else:
                    form1='=sum('+letter[colspan1+7]+str(col+1)+':'+letter[colspan1+7]+str(col1+2)+')'
                sheet.write(col+1,colspan1+7,form1,sub_currency_format)
                var+=i['additional_landed_cost']
                colspan1+=1
                
            sheet.write(col,colspan1+7,(p['former_cost']+var)/p['quantity'],currency_format)       
            sheet.write(col,colspan1+8,p['former_cost']+var,currency_format)            

        # form='=sum('+letter[colspan1+8]+str(col+1)+':'+letter[colspan1+8]+str(col1+2)+')'
        # sheet.write(col+1,colspan1+8,form,sub_currency_format)          