from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pack = fields.Char(string="Pack")
    custom_uom_id = fields.Many2one(
        'uom.uom',
    )

    @api.onchange('product_id')
    def _onchange_product_id_pack(self):
        """Auto-fill pack and custom_uom_id from product template."""
        if self.product_id:
            self.pack = self.product_id.pack
            self.custom_uom_id = self.product_id.custom_uom_id
        else:
            self.pack = 0.0
            self.custom_uom_id = False





  
  