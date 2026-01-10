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
            
############## New code for Free Scheme: starts ####################
class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_open_free_charges_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Free Product/(s)',
            'res_model': 'free.scheme.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id,},
        }

class FreeSchemeWizard(models.TransientModel):
    _name = "free.scheme.wizard"
    _description = "Free Scheme Wizard"

    order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        required=True
    )
    product_num = fields.Integer(string="Number of free product/(s)")
    product_id = fields.Many2one('product.template', string="Product")

    def action_apply_free_charges(self):
        self.ensure_one()
        if self.product_num <= 0:
            raise ValidationError(_("Free product quantity must be greater than zero."))

        order = self.order_id
        product = self.product_id.product_variant_id

        last_sequence = max(order.order_line.mapped('sequence') or [0])
        # Check if free product already exists
        free_line = order.order_line.filtered(
            lambda l: l.product_id == product and l.discount == 100
        )

        if free_line:
            free_line.product_uom_qty += self.product_num
        else:
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': self.product_num,
                'price_unit': product.lst_price,
                'discount': 100.0,
                'name': f"{product.name} (Free)",
                'sequence': last_sequence + 10,
            })

        order._compute_amounts()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
            'target': 'current',
        }
############## New code for Free Scheme: ends ####################