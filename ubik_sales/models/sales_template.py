from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ###### Code to populate pack on sale order line for product: starts ##########
    pack = fields.Char(string="Pack")
    custom_uom_id = fields.Many2one('uom.uom')

    @api.onchange('product_id')
    def _onchange_product_id_pack(self):
        """Auto-fill pack and custom_uom_id from product template."""
        if self.product_id:
            self.pack = self.product_id.pack
            self.custom_uom_id = self.product_id.custom_uom_id
        else:
            self.pack = 0.0
            self.custom_uom_id = False
    ###### Code to populate pack on sale order line for product: ends ##########


    ######## Code to open Open: Stock move wizard: starts ################
    def action_open_stock_move_smart(self):
        self.ensure_one()

        # Only confirmed sale orders
        if self.order_id.state == 'sale':
            move = self.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))[:1]
            if move:
                return {
                    'name': 'Open: Stock move',
                    'type': 'ir.actions.act_window',
                    'res_model': 'so.move.lot.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': dict(
                    self.env.context,
                    active_move_id=move.id,
                    default_sale_line_id=self.id),
                }
    ######## Code to open Open: Stock move wizard: ends ################

    stock_applied = fields.Boolean(string="Stock Applied", default=False)

############## Code relating to Delivery receipt validation on sale order line: starts #############################
class SoMoveLotWizard(models.Model):
    _name = "so.move.lot.wizard"
    _description = "Stock Move Wizard (Confirmed Sale)"

    picking_id = fields.Many2one('stock.picking', string="Delivery Order", required=False)
    sale_line_id = fields.Many2one('sale.order.line',required=True)
    line_ids = fields.One2many('so.move.lot.wizard.line', 'wizard_id', string="Lot/Serial Lines")
    product_id = fields.Many2one('product.product', compute='_compute_product_id', store=False)

    @api.depends('sale_line_id')
    def _compute_product_id(self):
        for wizard in self:
            wizard.product_id = wizard.sale_line_id.product_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        sale_line_id = self.env.context.get('default_sale_line_id')
        if not sale_line_id:
            return res

        sale_line = self.env['sale.order.line'].browse(sale_line_id)
        order = sale_line.order_id

        picking = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        move = picking.move_ids.filtered(
            lambda m: m.sale_line_id == sale_line and m.state not in ('done', 'cancel')
        )[:1]

        lines = []

        # CASE 1: Load from EXISTING move lines (reopen)
        if sale_line.stock_applied and move and move.move_line_ids:
            for ml in move.move_line_ids.sorted(
                key=lambda l: (
                    l.lot_id.expiration_date or fields.Date.max,
                    l.id
                )
            ):
                lines.append((0, 0, {
                    'location_id': ml.location_id.id,
                    'lot_id': ml.lot_id.id,
                    'expiration_date': ml.lot_id.expiration_date,
                    'qty': ml.quantity,
                    'product_uom_id': ml.product_uom_id.id,
                }))

        # CASE 2: First time open → load from quants
        else:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', sale_line.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ])

            # FEFO sort (Python-side, ORM safe)
            quants = quants.sorted(
                key=lambda q: (
                    q.lot_id.expiration_date,
                    q.lot_id.id
                )
            )
            for q in quants:
                lines.append((0, 0, {
                    'location_id': q.location_id.id,
                    'lot_id': q.lot_id.id,
                    'expiration_date': q.lot_id.expiration_date,
                    'qty': 0.0,
                    'product_uom_id': sale_line.product_uom.id,
                }))

        res.update({
            'sale_line_id': sale_line.id,
            'line_ids': lines,
        })
        return res

    def action_apply(self):
            self.ensure_one()
            sale_line = self.sale_line_id
            order = sale_line.order_id

            if not self.line_ids:
                raise ValidationError(_("Please add at least one lot."))

            total_qty = sum(self.line_ids.mapped('qty'))
            remaining_qty = sale_line.product_uom_qty - sale_line.qty_delivered

            if total_qty <= 0:
                raise ValidationError(_("Delivered quantity must be greater than zero."))

            if total_qty > remaining_qty:
                raise ValidationError(_("You cannot deliver more than remaining quantity."))

            picking = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if not picking:
                raise ValidationError(_("No delivery order found."))

            move = picking.move_ids.filtered(
                lambda m: m.sale_line_id == sale_line and m.state not in ('done', 'cancel')
            )
            if not move:
                raise ValidationError(_("No stock move found for this sale line."))

            # Reset move
            move.product_uom_qty = total_qty
            move.with_context(skip_picking_validation=True)._action_confirm()
            move.with_context(skip_picking_validation=True)._action_assign()

            # move.move_line_ids.unlink()
            move.move_line_ids.filtered(
                lambda ml: ml.product_id == self.product_id
            ).unlink()


            # Create move lines
            for line in self.line_ids:
                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'product_id': self.product_id.id,
                    'lot_id': line.lot_id.id,
                    'quantity': line.qty,          
                    'product_uom_id': sale_line.product_uom.id,
                    'location_id': line.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                })

            sale_line.stock_applied = True

            # CRITICAL FIX: Check ALL stockable sale order lines of the ENTIRE sale order
            all_stock_lines = order.order_line.filtered(
                lambda l:
                    l.product_id.type == 'product'
                    and not l.display_type
            )

            # Check ALL stockable sale order lines of the ENTIRE sale order
            all_stock_applied = all(l.stock_applied for l in all_stock_lines)

            # Debug logging to track what's happening
            _logger.info("=" * 50)
            _logger.info("Stock Applied Check for Order %s", order.name)
            for line in all_stock_lines:
                _logger.info("Line %s (Product: %s): stock_applied = %s, qty_delivered = %s/%s", 
                            line.id, line.product_id.name, line.stock_applied, 
                            line.qty_delivered, line.product_uom_qty)
            _logger.info("All stock applied: %s", all_stock_applied)
            _logger.info("=" * 50)

            if all_stock_applied:
                # Validate ONLY if ALL lines have stock_applied = True
                for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                    try:
                        # Force validate with context to ensure proper handling
                        picking.with_context(
                            skip_picking_validation=False,
                            skip_sms=True,
                            mail_notify_force_send=False
                        ).button_validate()
                        _logger.info("Successfully validated picking %s", picking.name)
                    except Exception as e:
                        _logger.error("Error validating picking %s: %s", picking.name, str(e))
                        raise ValidationError(_("Error validating delivery: %s") % str(e))

            return {'type': 'ir.actions.act_window_close'}

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        # Skip validation if context flag is set
        if self.env.context.get('skip_picking_validation'):
            return False
        
        # CRITICAL FIX: Prevent automatic validation of partial deliveries
        # Check if this validation is being triggered by our wizard
        if not self.env.context.get('allow_auto_validate'):
            # If not explicitly allowed, check if all lines are stock_applied
            for move in self.move_ids:
                if move.sale_line_id and not move.sale_line_id.stock_applied:
                    _logger.warning("Preventing validation of picking %s because line %s doesn't have stock_applied", 
                                  self.name, move.sale_line_id.id)
                    return False
        
        return super().button_validate()
    
    def _action_done(self):
        """
        Ensure backorder is created correctly ONLY for first picking
        """
        for picking in self:

            # Only apply to original picking (not backorders)
            if picking.backorder_id:
                continue

            for move in picking.move_ids:
                if move.sale_line_id:
                    move.product_uom_qty = move.sale_line_id.product_uom_qty

        return super()._action_done()


class SoMoveLotWizardLine(models.Model):
    _name = "so.move.lot.wizard.line"
    _description = "Lot Line"

    wizard_id = fields.Many2one('so.move.lot.wizard')
    lot_id = fields.Many2one('stock.lot', string="Lot/Serial", domain="[('id', 'in', available_lot_ids)]")
    expiration_date = fields.Date(readonly=True)
    qty = fields.Float(string="Quantity")
    location_id = fields.Many2one('stock.location', string="Source Location")
    product_uom_id = fields.Many2one('uom.uom')
    available_lot_ids = fields.Many2many('stock.lot', compute='_compute_available_lots')
    available_qty = fields.Float(string="Available Quantity", compute='_compute_available_qty', readonly=True)

    @api.depends('lot_id', 'location_id')
    def _compute_available_qty(self):
        Quant = self.env['stock.quant']
        for line in self:
            if not line.lot_id or not line.location_id:
                line.available_qty = 0.0
                continue
            quants = Quant.search([
                ('product_id', '=', line.wizard_id.sale_line_id.product_id.id),
                ('lot_id', '=', line.lot_id.id),
                ('location_id', '=', line.location_id.id),
            ])
            line.available_qty = sum(quants.mapped('quantity'))

    @api.depends('location_id', 'wizard_id.sale_line_id')
    def _compute_available_lots(self):
        Quant = self.env['stock.quant']
        for line in self:
            if not line.location_id or not line.wizard_id.sale_line_id:
                line.available_lot_ids = False
                continue

            product = line.wizard_id.sale_line_id.product_id

            line.available_lot_ids = Quant.search([
                ('product_id', '=', product.id),
                ('location_id', '=', line.location_id.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ]).mapped('lot_id')

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        self.expiration_date = self.lot_id.expiration_date
############## Code relating to Delivery receipt validation on sale order line: ends #############################

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