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
class ReportKardexMonth_wizard(models.Model):
    _name = "stock.kardex.month.wizard"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    product_id = fields.Many2one("product.product", string="Producto")
    date_to = fields.Datetime("Date To")
    date_from = fields.Datetime("Date From")


    def reporte(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        name = 'Reporte de Kardex Mensual'
        self.xslx_body(workbook, name)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': name  +  ".xlsx",
            'store_fname': name + ".xlsx",
            'type': 'binary',
        })

        url = "/web/content/%s?download=true" % (attachment.id)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def xslx_body(self, workbook, name):
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
        format_title_date = workbook.add_format(
            {'align': 'left', 'bold': False, 'border': 1, 'num_format': 'dd/mm/yyyy hh:mm'})
        format_title_date.set_align("vjustify")
        format_title_num = workbook.add_format({'align': 'right', 'bold': False, 'border': 1})
        format_title_num.set_num_format("#,##0.00")
        format_title3 = workbook.add_format({'align': 'left', 'bold': True, 'border': 1})
        format_title4 = workbook.add_format({'align': 'left', 'bold': True})
        format_title4.set_top(1)
        format_title3.set_bg_color("#b9b7b7")
        format_num_cost = workbook.add_format({'align': 'right', 'bold': False, 'border': 1})
        format_num_cost.set_num_format("#,##0.000000")
        sheet = workbook.add_worksheet(name)
        sheet.set_column(0, 5, 25)
        sheet.set_column(6, 10, 20)

        sheet.write(1, 0, _('Warehouse'), format_title4)
        sheet.write(2, 0, _('Product'), format_title4)
        sheet.write(4, 0, _('Date To'), format_title4)
        sheet.write(3, 0, _('Date From'), format_title4)

        sheet.write(1, 1, self.warehouse_id.display_name, format_title6)
        sheet.write(2, 1, self.product_id.display_name, format_title6)
        sheet.write(3, 1, self.date_from, format_title_date)
        sheet.write(4, 1, self.date_to, format_title_date)

        sheet.write(5, 0, _('Date'), format_title7)
        sheet.write(5, 1, _('Move'), format_title7)
        sheet.write(5, 2, _('Quantity'), format_title7)
        sheet.write(5, 3, _('Origin'), format_title7)
        sheet.write(5, 4, _('Destination'), format_title7)
        sheet.write(5, 5, _('Initial Amount'), format_title7)
        sheet.write(5, 6, _('Balance - Amounts'), format_title7)
        sheet.write(5, 7, _('Cost unit'), format_title7)
        sheet.write(5, 8, _('Valorization'), format_title7)
        i = 9
        unit_cost = 0.00
        for move in self.env['stock.move'].search([
            ('product_id', '=', self.product_id.id),
            ('date', '<=', self.date_from),
            ('date', '>=', self.date_to),
            ('state', '!=', 'cancel'),
        ], order="date"):
            if move.location_id.get_warehouse().id != self.warehouse_id.id \
                    and move.location_dest_id.get_warehouse().id != self.warehouse_id.id:
                continue
            unit_cost, i = self.write_sheet(move, format_title5, format_title_date, format_title_num, i, \
                                            sheet, unit_cost, format_num_cost)

            i += 1

    def write_sheet(self, move_id, format_title5, format_title_date, format_title_num, i, sheet, unit_cost,
                    format_num_cost):
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

        unit_cost = float_round(stock_layer.unit_cost,
                                precision_digits=6) or unit_cost
        i, product_qty = self.get_product_qty(format_title5, format_title_date, format_title_num, i, move_id,
                                              product_before_id, product_id, sheet, unit_cost)
        sheet.write(i, 0, move_id.date, format_title_date)
        sheet.write(i, 1, self._get_picking_name(move_id), format_title5)
        sheet.write(i, 2, product_qty, format_title_num)
        sheet.write(i, 3, self._get_location_name(move_id.location_id), format_title5)
        sheet.write(i, 4, self._get_location_name(move_id.location_dest_id), format_title5)
        sheet.write(i, 6, product_id.qty_available, format_title_num)
        sheet.write(i, 5, product_before_id.qty_available, format_title_num)
        sheet.write(i, 7, unit_cost, format_num_cost)
        sheet.write(i, 8, product_qty * unit_cost, format_title_num)
        # if self.env.user.has_group('base.group_no_one'):
        #     sheet.write(5, 9, _('movimiento id'), format_title7)
        #     sheet.write(5, 10, _('stock layer id'), format_title7)
        #     sheet.write(i, 9, move_id.id, format_title_num)
        #     sheet.write(i, 10, stock_layer.id, format_title_num)
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

    def write_sheet_scrap(self, move_id, format_title5, format_title_date, format_title_num, \
                          i, sheet, product_qty, product_before, unit_cost):
        sheet.write(i, 0, move_id.date_done, format_title_date)
        sheet.write(i, 1, self._get_scrap_name(move_id), format_title5)
        sheet.write(i, 2, move_id.scrap_qty, format_title_num)
        sheet.write(i, 3, self._get_location_name(move_id.location_id), format_title5)
        sheet.write(i, 4, self._get_location_name(move_id.scrap_location_id), format_title5)
        sheet.write(i, 5, product_qty, format_title_num)
        sheet.write(i, 6, product_before, format_title_num)
        sheet.write(i, 7, unit_cost, format_title_num)
        sheet.write(i, 8, move_id.scrap_qty * unit_cost, format_title_num)

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
