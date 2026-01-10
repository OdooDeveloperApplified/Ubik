from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class PurchaseTemplate(models.Model):
    _inherit = "purchase.order"

    order_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('domestic_sample', 'Domestic (Sample)'),
        ('domestic_update', 'Domestic (Will Update)'),
        ('export', 'Export'),
        ('export_sample', 'Export (Sample)'),
        
    ], string='Order Type', default = 'domestic')
    export_country = fields.Many2one('res.country', string="Export Country")
    delivery_place = fields.Char(string="Place of Delivery", default="Navagam")
    mode_of_transport = fields.Char(string="Mode of Transport")
    delivery_time = fields.Integer(string="Delivery Time (Days)")
    place_of_delivery = fields.Char(string="Place of Delivery")
   
    # code to populate mode of transport from vendor mot 
    @api.onchange('partner_id')
    def _onchange_partner_id_set_mot(self):
        if self.partner_id:
            self.mode_of_transport = self.partner_id.mode_of_transport

    # code to populate delivery time from vendor form view
    @api.onchange('partner_id')
    def _onchange_partner_id_set_delivery_time(self):
        if self.partner_id:
            self.delivery_time = self.partner_id.delivery_time
    
    # code to populate place of delivery from vendor form view
    @api.onchange('partner_id')
    def _onchange_partner_id_set_delivery_place(self):
        if self.partner_id:
            self.place_of_delivery = self.partner_id.place_of_delivery
            
    inspection_by = fields.Char(string="Inspection By", default="By us at our Premises")
    test_certificate = fields.Selection([
        ('required', 'Required'),
        ('not required', 'Not Required'),
    ], string='COA/Test Certificate', default = 'required')

    # Code to show pack column if pack is applicable for product on order lines, which was required for PO report generation
    def _get_packaging_flag(self):
        self.ensure_one()
        return any(self.order_line.mapped('product_packaging_id'))
    
    # Code to add received quantity column in product-> purchased smart button-> purchase history view
    received_qty = fields.Float(string="Received Qty",compute="_compute_received_qty")
    

    def _compute_received_qty(self):
        for order in self:
            # Get active product from context (coming from smart button)
            product_id = self.env.context.get('active_id')

            if not product_id:
                order.received_qty = 0
                continue

            # Sum received qty of only this product
            lines = order.order_line.filtered(lambda l: l.product_id.id == product_id)
            order.received_qty = sum(lines.mapped('qty_received'))
    
    export_country_label = fields.Char(string="Export Country Label", compute="_compute_export_country_label", store=False)

    @api.depends('order_type', 'export_country')
    def _compute_export_country_label(self):
        for rec in self:
            if rec.order_type == 'export' and rec.export_country:
                rec.export_country_label = rec.export_country.name
            else:
                rec.export_country_label = ""

    ########## (NEW) code to split purchase order lines by lot numbers: starts ##########
    show_lot_wise = fields.Boolean(string="Show Lot-wise Data", default=False, copy=False)
    lot_id = fields.Many2one('stock.lot', string="Lot", readonly=True)
    def action_split_lines_by_lot(self):
        PurchaseLine = self.env['purchase.order.line']

        for order in self:
            # Remove previously generated lot-split lines
            old_lines = order.order_line.filtered(lambda l: l.is_lot_split_line)
            old_lines.unlink()

            for line in order.order_line.filtered(
                lambda l: not l.display_type and not l.is_lot_split_line
            ):
                moves = line.move_ids.filtered(lambda m: m.state == 'done')
                if not moves:
                    continue

                lot_qty_map = {}

                for move in moves:
                    for ml in move.move_line_ids:
                        if ml.lot_id:
                            lot_qty_map.setdefault(ml.lot_id.name, 0.0)
                            lot_qty_map[ml.lot_id.name] += ml.quantity

                if not lot_qty_map:
                    continue

                seq = line.sequence + 0.01

                # Create lot-wise NOTE lines under the current line
                for lot_name, qty in lot_qty_map.items():
                    PurchaseLine.create({
                        'order_id': order.id,
                        'display_type': 'line_note',
                        'name': f"Lot {lot_name} → Qty Received: {qty}",
                        'product_qty': 0.0,
                        'sequence': seq,
                        'is_lot_split_line': True,
                    })
                    seq += 0.01

    def action_toggle_lot_wise(self):
        for order in self:
            if order.show_lot_wise:
                # HIDE → remove lot split lines
                order.order_line.filtered(lambda l: l.is_lot_split_line).unlink()
                order.show_lot_wise = False
            else:
                # SHOW → reuse existing logic
                order.action_split_lines_by_lot()
                order.show_lot_wise = True
    ########## code to split purchase order lines by lot numbers: ends ##########

    ############# (NEW)code to add purchase status field in purchase order form view : starts #########
    order_status = fields.Char(string="Order Status",compute="_compute_order_status")

    @api.depends('order_line.product_uom_qty', 'order_line.qty_received')
    def _compute_order_status(self):
        for order in self:
            # Ignore note/section/lot split lines
            lines = order.order_line.filtered(
                lambda l: not l.display_type and not l.is_lot_split_line
            )

            if not lines:
                order.order_status = "Pending"
                continue

            # If any line is not fully received → Pending
            if any(line.qty_received < line.product_uom_qty for line in lines):
                order.order_status = "Pending"
            else:
                order.order_status = "Closed"
    ############# code to add purchase status field in purchase order form view : ends #########

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_price = fields.Float(string='MRP', related='product_id.list_price',)
    hsn_code = fields.Char(string='HSN Code', related='product_id.l10n_in_hsn_code')
    pack_size = fields.Char(string="Pack Size")
    pack_size_uom = fields.Char(string="Pack UOM")
    display_pack_size = fields.Char(string="Pack Size (Display)", compute="_compute_display_pack_size")

    # code to populate pack size displayed on product form view on purchase order lines
    @api.depends('product_id')
    def _compute_display_pack_size(self):
        for line in self:
            tmpl = line.product_id.product_tmpl_id

            line.pack_size = tmpl.pack_size
            line.pack_size_uom = tmpl.pack_size_uom_id.name if tmpl.pack_size_uom_id else False

            if tmpl.pack_size and tmpl.pack_size_uom_id:
                line.display_pack_size = f"{tmpl.pack_size} {tmpl.pack_size_uom_id.name}"
            else:
                line.display_pack_size = tmpl.pack_size or ""
    
    # code to add pending quantity field in purchase history tree view
    pending_qty = fields.Float(string="Pending Qty", compute="_compute_pending_qty", store=False)

    @api.depends('product_uom_qty', 'qty_received')
    def _compute_pending_qty(self):
        for line in self:
            ordered = line.product_uom_qty or 0
            received = line.qty_received or 0
            line.pending_qty = ordered - received
    
    # code to populate product related pack
    pack = fields.Char(string="Pack")
    custom_uom_id = fields.Many2one('uom.uom')
    display_product_pack = fields.Char(string="Product Pack", compute="_compute_display_product_pack")

    @api.depends('product_id')
    def _compute_display_product_pack(self):
        for line in self:
            tmpl = line.product_id.product_tmpl_id

            # Assign raw values
            line.pack = tmpl.pack
            line.custom_uom_id = tmpl.custom_uom_id

            # Display format: "<pack> <uom>"
            if tmpl.pack and tmpl.custom_uom_id:
                line.display_product_pack = f"{tmpl.pack} {tmpl.custom_uom_id.name}"
            else:
                line.display_product_pack = tmpl.pack or ""

    @api.onchange('product_id')
    def _onchange_product_id_pack(self):
        """Auto-fill pack and custom_uom_id from product template."""
        if self.product_id:
            tmpl = self.product_id.product_tmpl_id
            self.pack = tmpl.pack
            self.custom_uom_id = tmpl.custom_uom_id
        else:
            self.pack = False
            self.custom_uom_id = False
    
    mrp_display = fields.Char(string="MRP Display", compute="_compute_mrp_display", store=False)

    @api.depends('order_id.order_type', 'sale_price')
    def _compute_mrp_display(self):
        for line in self:
            if line.order_id.order_type == "export":
                line.mrp_display = "Without"

            elif line.order_id.order_type == "sample":
                line.mrp_display = "Sample"

            elif line.order_id.order_type == "will_update":
                line.mrp_display = "Will Update"

            else:  # domestic or anything else
                line.mrp_display = line.sale_price
    
    purchase_status = fields.Char(string="Status",compute="_compute_purchase_status", store=False)

    ######### code to add purchase status field in purchase history tree view (found as a smart button in product form view named Purchases) #########
    @api.depends('product_uom_qty', 'qty_received')
    def _compute_purchase_status(self):
        for line in self:
            ordered = line.product_uom_qty or 0
            received = line.qty_received or 0

            if ordered == received:
                line.purchase_status = "Closed"
            else:
                line.purchase_status = "Pending"
    
    lot_numbers = fields.Char(string="Lot Numbers", compute="_compute_lot_numbers", store=False)

    def _compute_lot_numbers(self):
        for line in self:
            lot_names = set()

            # Stock moves created from this PO line
            moves = line.move_ids.filtered(lambda m: m.state == 'done')

            # Move lines contain lot info
            for move in moves:
                for move_line in move.move_line_ids:
                    if move_line.lot_id:
                        lot_names.add(move_line.lot_id.name)

            line.lot_numbers = ', '.join(sorted(lot_names)) if lot_names else ''
    ############ code to add purchase status field in purchase history tree view #########
    
    # (NEW) Field to mark lot split lines to show under purchase order lines
    is_lot_split_line = fields.Boolean(string="Lot Split Line", default=False, copy=False, index=True)


# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     def action_post(self):
#         res = super().action_post()

#         for move in self:
#             # Only vendor bills
#             if move.move_type != 'in_invoice':
#                 continue

#             # Get related purchase orders
#             purchase_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id')
#             purchase_orders = purchase_orders.filtered(lambda po: po.state == 'purchase')

#             for po in purchase_orders:
#                 # Get incoming pickings
#                 pickings = po.picking_ids.filtered(
#                     lambda p: p.state in ('confirmed', 'assigned')
#                     and p.picking_type_id.code == 'incoming'
#                 )

#                 for picking in pickings:
#                     # Set done quantities
#                     for move_line in picking.move_line_ids:
#                         if move_line.quantity == 0:
#                             move_line.quantity = move_line.product_uom_qty

#                     # Validate receipt
#                     picking.button_validate()

#         return res








