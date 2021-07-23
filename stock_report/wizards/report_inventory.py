# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import base64
from io import BytesIO
from itertools import count, chain
from functools import partial
from collections import defaultdict, Counter
import xlsxwriter
from datetime import datetime, timedelta
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from functools import lru_cache
from odoo.tools.float_utils import float_round, float_is_zero


_logger = logging.getLogger(__name__)

class Report_Kardex_wizard(models.Model):
    _name = "stock.kardex.wizard"

    warehouse_id = fields.Many2one("stock.warehouse",string="Warehouse")
    product_id = fields.Many2one("product.product",string="Producto")
    date_from = fields.Datetime("Fecha Hasta", default=fields.Datetime.now)


    def reporte(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        name = 'Reporte de Kardex'
        self.xslx_body(workbook, name)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': name + ".xlsx",
            'store_fname': name + ".xlsx",
            'type': 'binary',
        })

        url = "/web/content/%s?download=true" % (attachment.id)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def xslx_body(self,workbook,name):
        bold = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#CFC8C6'})
        bold.set_center_across()
        format_title = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})
        format_title.set_center_across()
        format_title.set_align('vjustify')
        format_title_b = workbook.add_format({'align': 'center', 'bold': False, 'border': 1})
        format_title_b.set_center_across()
        format_title_b.set_text_wrap()
        format_title_b.set_align('vjustify')
        format_title_1 = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})

        format_title2 = workbook.add_format({'align': 'left', 'bold': True})
        format_title7 = workbook.add_format({'align': 'left', 'bold': True, 'border': 1})
        format_title6 = workbook.add_format({'align': 'left', 'bold': True})
        format_title7.set_text_wrap()
        format_title7.set_align('vjustify')
        format_title5 = workbook.add_format({'align': 'left', 'bold': False, 'border': 1})
        format_title5.set_align('vjustify')
        format_title_num_bold = workbook.add_format({'align': 'left', 'bold': False, 'border': 1})
        format_title_num_bold.set_align('vjustify')
        format_title_num_bold.set_num_format("0.00")
        format_title_date = workbook.add_format({'align': 'left', 'bold': False, 'border': 1, 'num_format': 'dd/mm/yyyy hh:mm'})
        format_title_date.set_align("vjustify")
        format_title_date_n = workbook.add_format(
            {'align': 'left', 'bold': False, 'num_format': 'dd/mm/yyyy hh:mm'})
        format_title_date_n.set_align("vjustify")
        format_title_num = workbook.add_format({'align': 'right', 'bold': False,'border': 1})
        format_title_num.set_num_format("#,##0.00")
        format_title3 = workbook.add_format({'align': 'left', 'bold': True, 'border': 1})
        format_title4 = workbook.add_format({'align': 'left', 'bold': True})
        format_title4.set_top(1)
        format_title3.set_bg_color("#b9b7b7")
        format_num_cost = workbook.add_format({'align': 'right', 'bold': False,'border': 1})
        format_num_cost.set_num_format("#,##0.000000")

        sheet = workbook.add_worksheet(name)
        sheet.set_column(0, 5, 25)
        sheet.set_column(6, 16, 20)

        sheet.write(1, 0, _('Warehouse'), format_title4)
        sheet.write(2, 0, _('Product'), format_title4)
        sheet.write(3, 0, _('Date To'), format_title4)
        sheet.write(4, 0, _('Company'), format_title4)
        sheet.write(6, 0, _('Valuación'), format_title4)

        sheet.write(1, 1, self.warehouse_id.display_name or "", format_title6)
        sheet.write(2, 1, self.product_id.display_name or "", format_title6)
        sheet.write(3, 1, self.date_from, format_title_date_n)
        sheet.write(4, 1, self.env.company.name or "", format_title6)
        sheet.write(6, 1, "PROMEDIO", format_title6)


        sheet.write(8, 0, _('Date'), format_title7)
        sheet.write(8, 1, _('Code'), format_title7)
        sheet.write(8, 2, _('Transaction'), format_title7)
        sheet.write(8, 3, _('N° Document'), format_title7)
        sheet.write(8, 4, _('Cliente/ \n Proveedor'), format_title7)
        sheet.write(8, 5, _('Warehouse'), format_title7)
        sheet.write(8, 6, _('Reference Origin'), format_title7)
        sheet.write(8, 7, _('Reference Destination'), format_title7)
        sheet.merge_range('I8:K8', _('Entry'), format_title7)
        sheet.write(8, 8, _('Quantity'), format_title7)
        sheet.write(8, 9, _('Cost unit'), format_title7)
        sheet.write(8, 10, _('Cost Total'), format_title7)
        sheet.merge_range('L8:N8', _('Outgoing'), format_title7)
        sheet.write(8, 11, _('Quantity'), format_title7)
        sheet.write(8, 12, _('Cost unit'), format_title7)
        sheet.write(8, 13, _('Cost Total'), format_title7)
        sheet.merge_range('O8:Q8', _('Total Balance'), format_title7)
        sheet.write(8, 14, _('Quantity'), format_title7)
        sheet.write(8, 15, _('Cost unit'), format_title7)
        sheet.write(8, 16, _('Cost Total'), format_title7)

        i = 9
        unit_cost = 0.00
        search = []
        if self.product_id.id:
            search.append(('product_id','=',self.product_id.id))
        search.append(('date','<=',self.date_from))
        search.append(('state','!=','cancel'))
        for move in self.env['stock.move'].search(search, order="date"):
            if move.location_id.get_warehouse().id != self.warehouse_id.id \
                    and move.location_dest_id.get_warehouse().id != self.warehouse_id.id:
                continue
            unit_cost, i = self.write_sheet(move,format_title5, format_title_date, format_title_num, i,\
                                            sheet, unit_cost, format_num_cost)

            i += 1

    def write_sheet(self, move_id, format_title5, format_title_date, format_title_num, i,
                    sheet, unit_cost, format_num_cost):
        product_id = move_id.product_id.with_context({
            'warehouse': self.warehouse_id.id,
            'to_date': move_id.date
        })
        product_before_id = move_id.product_id.with_context({
            'warehouse': self.warehouse_id.id,
            'to_date': move_id.date - timedelta(seconds=1)
        })
        stock_layer = self.env['stock.valuation.layer'].search([
            ('stock_move_id', '=', move_id.id), ('product_id', '=', product_id.id)
        ], limit=1)
        unit_cost = float_round(stock_layer.unit_cost, precision_digits=6) or unit_cost
        i, product_qty = self.get_product_qty(format_title5, format_title_date, format_title_num, i, move_id,
                                          product_before_id, product_id, sheet, unit_cost)
        sheet.write(i, 0, move_id.date, format_title_date)
        sheet.write(i, 1, "", format_title5)
        sheet.write(i, 2, move_id.picking_code, format_title5)
        sheet.write(i, 3, self._get_scrap_name(move_id), format_title5)
        sheet.write(i, 4, move_id.restrict_partner_id.name or "", format_title5)
        sheet.write(i, 5, move_id.warehouse_id.name or "", format_title5)
        sheet.write(i, 6, self._get_location_name(move_id.location_id), format_title5)
        sheet.write(i, 7, self._get_location_name(move_id.location_dest_id), format_title5)
        if move_id.picking_code != 'outgoing':
            sheet.write(i, 8, product_qty, format_title_num)
            sheet.write(i, 9, unit_cost, format_title_num)
            sheet.write(i, 10, product_qty * unit_cost, format_title_num)
            sheet.write(i, 11, 0.00, format_title_num)
            sheet.write(i, 12, 0.00, format_title_num)
            sheet.write(i, 13, 0.00, format_title_num)
        else:
            sheet.write(i, 8, 0.00, format_title_num)
            sheet.write(i, 9, 0.00, format_title_num)
            sheet.write(i, 10, 0.00, format_title_num)
            sheet.write(i, 11, product_qty, format_title_num)
            sheet.write(i, 12, unit_cost, format_title_num)
            sheet.write(i, 13, product_qty * unit_cost, format_title_num)
        sheet.write(i, 14, product_id.qty_available, format_title_num)
        sheet.write(i, 15, unit_cost, format_title_num)
        sheet.write(i, 16, product_id.qty_available * unit_cost, format_title_num)
        return unit_cost, i

    def get_product_qty(self, format_title5, format_title_date, format_title_num, i, move_id, \
                    product_before_id, product_id, sheet, unit_cost):
        product_qty = 0.00
        if self.env['stock.scrap'].search([
            ('picking_id.name', '=', self._get_picking_name(move_id))
        ]):
            scrap_ids = self.env['stock.scrap'].search([
                ('picking_id.name', '=', self._get_picking_name(move_id))
            ])
            scrap_value = 0
            for scrap_id in scrap_ids:
                scrap_value += scrap_id.scrap_qty
                self.write_sheet_scrap(scrap_id, format_title5, format_title_date, format_title_num, \
                                       i, sheet, product_id.qty_available, \
                                       product_before_id.qty_available, unit_cost)
                i += 1
            product_qty -= scrap_value
        product_qty += move_id.product_qty
        if move_id.location_id.get_warehouse().id == self.warehouse_id.id \
                and move_id.location_dest_id.get_warehouse().id != self.warehouse_id.id:
            product_qty = -product_qty

        return i, product_qty

    def write_sheet_scrap(self, move_id, format_title5, format_title_date, format_title_num,\
                          i, sheet, product_qty, product_before, unit_cost):
        sheet.write(i, 0, move_id.date_done, format_title_date)
        sheet.write(i, 1, "", format_title5)
        sheet.write(i, 2, self._get_scrap_name(move_id) or "", format_title5)
        sheet.write(i, 3, "DESECHO", format_title5)
        sheet.write(i, 4, move_id.owner_id.name or "", format_title5)
        sheet.write(i, 5, self._get_scrap_warehouse(move_id) or "", format_title5)
        sheet.write(i, 6, self._get_location_name(move_id.location_id), format_title5)
        sheet.write(i, 7, self._get_location_name(move_id.scrap_location_id), format_title5)
        sheet.write(i, 8, 0.00, format_title_num)
        sheet.write(i, 9, 0.00, format_title_num)
        sheet.write(i, 10, 0.00, format_title_num)
        sheet.write(i, 11, move_id.scrap_qty, format_title_num)
        sheet.write(i, 12, unit_cost, format_title_num)
        sheet.write(i, 13, unit_cost, format_title_num)
        sheet.write(i, 14, product_qty, format_title_num)
        sheet.write(i, 15, unit_cost, format_title_num)
        sheet.write(i, 16, move_id.scrap_qty * unit_cost, format_title_num)

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_scrap_warehouse(move_id):
        return move_id.move_id.warehouse_id.name


    @staticmethod
    @lru_cache(maxsize=None)
    def _get_scrap_name(move_id):
        return move_id.name

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_picking_name(move_id):
        return move_id.reference

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_location_name(location):
        return location.display_name


class ReportInventory_wizard(models.Model):
    _name = "stock.report.wizard"

    date = fields.Datetime(string="Fecha Hasta",default=fields.Datetime.now)


    def report(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        name = 'Reporte de Kardex'
        self.xslx_body(workbook,name)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': name + ".xlsx",
            'store_fname': name + ".xlsx",
            'type': 'binary',
            # 'datas_fname': name+'.xlsx',
        })

        url = "/web/content/%s?download=true" % (attachment.id)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def xslx_body(self,workbook,name):
        bold = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#CFC8C6'})
        bold.set_center_across()
        format_title = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})
        format_title.set_center_across()
        format_title.set_align('vjustify')
        format_title_b = workbook.add_format({'align': 'center', 'bold': False, 'border': 1})
        format_title_b.set_center_across()
        format_title_b.set_text_wrap()
        format_title_b.set_align('vjustify')
        format_title_1 = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})

        format_title2 = workbook.add_format({'align': 'left', 'bold': True})
        format_title7 = workbook.add_format({'align': 'left', 'bold': True, 'border': 1})
        format_title6 = workbook.add_format({'align': 'left', 'bold': True, 'border': 1})
        format_title7.set_text_wrap()
        format_title7.set_align('vjustify')
        format_title5 = workbook.add_format({'align': 'left', 'bold': False, 'border': 1})
        format_title5.set_align('vjustify')
        format_title_num_bold = workbook.add_format({'align': 'left', 'bold': False, 'border': 1})
        format_title_num_bold.set_align('vjustify')
        format_title_num_bold.set_num_format("#,##0.00")
        format_title_date = workbook.add_format({'align': 'left', 'bold': False, 'border': 1, 'num_format': 'dd/mm/yy hh:mm'})
        format_title_date.set_align("vjustify")
        format_title_date_b = workbook.add_format(
            {'align': 'left', 'bold': False, 'num_format': 'dd/mm/yy hh:mm'})
        format_title_date.set_align("vjustify")
        format_title_num = workbook.add_format({'align': 'right', 'bold': False,'border': 1})
        format_title_num.set_num_format("#,##0.00")
        format_title3 = workbook.add_format({'align': 'left', 'bold': True, 'border': 1})
        format_title4 = workbook.add_format({'align': 'left', 'bold': True})
        format_title4.set_top(1)
        format_title3.set_bg_color("#b9b7b7")
        sheet = workbook.add_worksheet(name)
        sheet.write(0, 0, _('Date to'), format_title2)
        sheet.write(0, 1, self.date, format_title_date_b)

        i = 2

        sheet.write(i, 0, _('Product'), format_title7)
        sheet.set_column(0,7, 30)
        sheet.write(i, 1, _('Location'), format_title7)
        sheet.write(i, 2, _('Warehouse'), format_title7)
        sheet.write(i, 3, _('Quantity On Hand'), format_title7)
        sheet.write(i, 4, _('Forecast Quantity'), format_title7)
        sheet.write(i, 5, _('Free To Use Quantity'), format_title7)
        sheet.write(i, 6, _('Incoming'), format_title7)
        sheet.write(i, 7, _('Outgoing'), format_title7)
        i += 1

        for location_id in self.env['stock.location'].search([('usage', '=', 'internal')]):
            warehouse_name = location_id.get_warehouse().display_name
            location_name = location_id.display_name
            product_ids = self.env['product.product'].with_context({
                'location': location_id.id,
                'to_date': self.date
            }).search([])
            res = product_ids._compute_quantities_dict(
                self._context.get('lot_id'), self._context.get('owner_id'),
                self._context.get('package_id'), self._context.get('from_date'),
                self.date
            )
            for product in product_ids:
                # product_id._compute_quantities() ESTA LINEA ES DONDE, pasar los datos a un diccionario
                qty_available = res[product.id][
                    'qty_available']  # self.method_name(location_id,self.date,product_id.id)
                if qty_available == 0.00 or product.type == "service":
                    continue
                sheet.write(i, 0, self.product_name(product), format_title5)
                sheet.write(i, 1, location_name, format_title_b)
                sheet.write(i, 2, warehouse_name, format_title_b)
                sheet.write(i, 3, qty_available, format_title_num)
                sheet.write(i, 4, res[product.id]['virtual_available'], format_title_num)
                sheet.write(i, 5, res[product.id]['free_qty'], format_title_num)
                sheet.write(i, 6, res[product.id]['incoming_qty'], format_title_num)
                sheet.write(i, 7, res[product.id]['outgoing_qty'], format_title_num)
                i += 1

    @staticmethod
    @lru_cache(maxsize=None)
    def product_name(product_id):
        return product_id.display_name
