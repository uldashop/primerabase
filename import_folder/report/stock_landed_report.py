# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.addons.stock_landed_costs.models import product
from datetime import date, timedelta
SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]
class StockLandedReport(models.Model):
    _name = "stock.landed.report"
    _description = "Gasto de envio Reporte"
    _auto = False
    _rec_name = 'date'
    #_order = 'date desc'

    ###datos cabecera
    name = fields.Char('Referencia', readonly=True)
    account_journal_id = fields.Many2one('account.journal', 'Diario', readonly=True)
    account_move_id = fields.Many2one('account.move', 'Movimiento de Cuenta', readonly=True)
    date = fields.Datetime('Fecha', readonly=True)
    amount_total = fields.Float('Monto Total', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
        ], string='Estado', readonly=True)
    cost_id = fields.Many2one('stock.landed.cost', 'Costo #', readonly=True)
    
    ####cost_line
    product_id = fields.Many2one('product.product', 'Producto', readonly=True)
    account_id = fields.Many2one('account.account', 'Cuenta', readonly=True)
    split_method = fields.Selection(SPLIT_METHOD, string='Método de división', required=True)
    price_unit = fields.Float('Costo Unitario', required=True)
    nbr = fields.Integer('# de Lineas', readonly=True)

    ###valuation_line
    name_product = fields.Char('Nombre del Producto', readonly=True)
    quantity = fields.Float('Cantidad', default=1.0,digits=0, required=True)
    weight = fields.Float('Peso', default=1.0)
    volume = fields.Float('volumen', default=1.0)
    former_cost = fields.Float('Costo Anterior')
    former_cost_per_unit = fields.Float('Costo Anterior(Por unidad)',digits=0, store=True)
    additional_landed_cost = fields.Float('Costo Adicional de Aterrizaje')
    final_cost = fields.Float('Costo Final',digits=0, store=True)
    

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ ="""---cost lines---
                    min(l.id) as id,
                    l.product_id as product_id,
                    l.account_id as account_id,
                    l.split_method as split_method,
                    l.price_unit as price_unit,
                    count(*) as nbr,
                    
                    ---head--
                    s.id as cost_id,
                    s.name as name,
                    s.account_journal_id as account_journal_id,
                    s.account_move_id as account_move_id,
                    s.date as date,
                    s.amount_total as amount_total,
                    s.state as state,

                    --- valuation lines---
                    sv.name as name_product,
                    sv.weight as weight,
                    sv.volume as volume,
                    sv.quantity as quantity,
                    sv.former_cost as former_cost,
                    sv.additional_landed_cost as additional_landed_cost,
                    sv.final_cost """
                    #sum(sv.former_cost_per_unit)
                    #sv.former_cost_per_unit as former_cost_per_unit,

        
        for field in fields.values():
            select_ += field

        from_ = """ stock_landed_cost_lines l
                    join stock_landed_cost s on l.cost_id=s.id
                    left join product_product p on (l.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join account_account aa on l.account_id=aa.id
                    left join account_journal aj on s.account_journal_id=aj.id
                    left join account_move am on s.account_move_id=am.id
                    left join stock_valuation_adjustment_lines sv on sv.cost_line_id=l.id
                    %s """ % from_clause

        groupby_ = """  l.product_id
                        ,l.account_id
                        ,l.split_method
                        ,l.price_unit
                        ,s.name
                        ,s.account_journal_id
                        ,s.account_move_id
                        ,s.date
                        ,s.amount_total
                        ,s.state
                        ,sv.name
                        ,sv.cost_line_id
                        ,sv.weight
                        ,sv.volume
                        ,sv.quantity
                        
                        ,sv.former_cost
                        ,sv.additional_landed_cost
                        ,sv.final_cost
                        ,s.id %s """ % (groupby)
                        #,sv.former_cost_per_unit
        return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

    @api.model
    def init(self):
        print('ingresa?')
        # self._table = stock_landed_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
