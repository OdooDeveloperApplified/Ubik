from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class PurchaseTemplate(models.Model):
    _inherit = "purchase.order"

   
    order_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('export', 'Export'),
        ('sample', 'Sample'),
        ('will_update', 'Will Update'),
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
    
    export_country_label = fields.Char(
        string="Export Country Label",
        compute="_compute_export_country_label",
        store=False
    )

    @api.depends('order_type', 'export_country')
    def _compute_export_country_label(self):
        for rec in self:
            if rec.order_type == 'export' and rec.export_country:
                rec.export_country_label = rec.export_country.name
            else:
                rec.export_country_label = ""


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
    
    mrp_display = fields.Char(
        string="MRP Display",
        compute="_compute_mrp_display",
        store=False
    )

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

    @api.depends('product_uom_qty', 'qty_received')
    def _compute_purchase_status(self):
        for line in self:
            ordered = line.product_uom_qty or 0
            received = line.qty_received or 0

            if ordered == received:
                line.purchase_status = "Closed"
            else:
                line.purchase_status = "Pending"

