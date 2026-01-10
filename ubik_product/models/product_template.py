from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Field to link the product to the group name
    group_id = fields.Many2one("group.name", string="Group Name")
    pack = fields.Char(string="Pack")
    custom_uom_id = fields.Many2one('uom.uom', string='Custom Unit of Measure')
    shelf_life = fields.Char(string="Shelf Life")
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    vendor_criteria_line_ids = fields.One2many('product.vendor.criteria.line','product_id', string="Vendor Criteria Lines")
    pack_size = fields.Char(string="Pack Size")
    pack_size_uom_id = fields.Many2one('uom.uom', string='Custom Pack Unit of Measure')

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Populate criteria lines based on selected vendor."""
        for product in self:
            if not product.vendor_id:
                product.vendor_criteria_line_ids = [(5, 0, 0)]
                return

            # Fetch all vendor-specific acceptance criteria
            vendor_criteria = self.env['vendor.acceptance.criteria'].search([
                ('vendor_id', '=', product.vendor_id.id)
            ])

            # Prepare new lines for product
            new_lines = []
            for line in vendor_criteria:
                new_lines.append((
                    0, 0,
                    {
                        'vendor_id': line.vendor_id.id,
                        'criteria_id': line.criteria_id.id,   
                    }
                ))

            # Replace existing lines
            product.vendor_criteria_line_ids = [(5, 0, 0)] + new_lines
    
    #Product Master Specification fields

    ####### Technical parameter acceptance criteria ###############
    color = fields.Char(string="Color")
    spreadibility = fields.Char(string="Spreadibility")
    consistency = fields.Char(string="Consistency")

    ####### Packaging criteria ###############
    # For container/strip
    container_type = fields.Char(string="Container Type")
    container_size = fields.Char(string="Container Size (Approx. in mm)")

    # For cap
    cap_type = fields.Char(string="Cap Type")
    cap_size = fields.Char(string="Cap Size (Approx. in mm)")

    # For label
    label_type = fields.Char(string="Label Type")
    label_size = fields.Char(string="Label Size (Approx. in mm)")

    ####### Secondary Packaging criteria ###############
    # For monocarton
    monocarton_type = fields.Char(string="Monocarton Type")
    monocarton_size = fields.Char(string="Monocarton Size")

    ####### Master Packaging criteria ###############
    master_pack_type = fields.Char(string="Master Packaging Type")
    master_pack_size = fields.Char(string="Master Packaging Size")

    total_pcs_per_box = fields.Float(string="Total Pieces/Box") 
    
    inspection_line_ids = fields.Many2many(
        "inspection.report.line",
        compute="_compute_inspection_lines",
        string="Inspection Reports",
        store=False
    )

    def _compute_inspection_lines(self):
        for template in self:
            products = template.product_variant_ids.ids
            lines = self.env['inspection.report.line'].search([
                ('product_id', 'in', products)
            ])
            template.inspection_line_ids = lines

    
    def action_open_inspection_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inspection Reports',
            'res_model': 'inspection.report.line',
            'view_mode': 'list,form',
            'views': [
            (self.env.ref('ubik_inventory.view_inspection_report_line_tree_custom').id, 'list'),
            (self.env.ref('ubik_inventory.view_inspection_report_line_form_detailed').id, 'form')
        ],
            'domain': [('id', 'in', self.inspection_line_ids.ids)],
            'context': {'default_product_id': self.id},
        }

   
class GroupName(models.Model):
    _name = 'group.name'
    _description = 'Create Group Names'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name")

class AcceptanceCriteriaMaster(models.Model):
    _name = 'acceptance.criteria'
    _description = 'Acceptance Criteria'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name")

class VendorAcceptanceCriteria(models.Model):
    _name = 'vendor.acceptance.criteria'
    _description = 'Vendor Acceptance Criteria Mapping'

    vendor_id = fields.Many2one('res.partner', string="Vendor", domain=[('supplier_rank', '>', 0)])
    criteria_id = fields.Many2one('acceptance.criteria', string="Parameters")
   

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_acceptance_ids = fields.One2many('vendor.acceptance.criteria', 'vendor_id', string="Parameters")
    product_vendor_criteria_ids = fields.One2many('product.vendor.criteria.line', 'vendor_id', string="Product Vendor Criteria Lines")

class ProductVendorCriteriaLine(models.Model):
    _name = 'product.vendor.criteria.line'
    _description = 'Product Vendor Criteria Line'

    product_id = fields.Many2one('product.template', string="Product")
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    criteria_id = fields.Many2one('acceptance.criteria', string="Parameter")
    value = fields.Char(string="Value")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill vendor_id when line is created from product form."""
        if self.product_id and self.product_id.vendor_id:
            self.vendor_id = self.product_id.vendor_id


        


