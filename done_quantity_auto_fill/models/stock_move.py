from odoo import fields, models


class StockMove(models.Model):
    """inheriting the stock_move for updating the done qty """
    _inherit = 'stock.move'

    product_select = fields.Boolean(string="Select",
                                    help="Select products from order line",
                                    copy=False)
