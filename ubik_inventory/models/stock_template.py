from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class InspectionReportLine(models.Model):
    _name = 'inspection.report.line'
    _description = 'Inspection Report Line'

    name = fields.Char(string='Line Reference', required=True, copy=False, readonly=True, default='New')
    report_id = fields.Many2one('inspection.report', string="Inspection Report")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    inspection_release_no = fields.Char(string='Inspection Release Number')
    quantity = fields.Float(string='Total Received Quantity')
    sample_quantity = fields.Float(string='Sample Quantity', help="Number of units actually inspected")
    is_sample_locked = fields.Boolean(string="Is Sample Quantity Locked",compute="_compute_is_sample_locked",store=False)
    @api.depends('sample_quantity', 'report_id.state')
    def _compute_is_sample_locked(self):
        """Lock sample quantity once it’s entered and the record is saved."""
        for line in self:
            if line.sample_quantity and line.id:
                line.is_sample_locked = True
            else:
                line.is_sample_locked = False

    balance_quantity = fields.Float(string='Remaining Quantity', compute='_compute_balance_quantity', store=True)
    batch_no = fields.Char(string='Batch Number',compute='_compute_batch_no_from_lot')

    @api.depends('product_id', 'report_id.picking_id')
    def _compute_batch_no_from_lot(self):
        """Auto-fetch lot number from the original receipt move line."""
        for line in self:
            batch = False
            if line.report_id and line.report_id.picking_id and line.product_id:
                receipt_ml = line.report_id.picking_id.move_line_ids.filtered(
                    lambda ml: ml.product_id.id == line.product_id.id
                )
                if receipt_ml:
                    batch = receipt_ml[0].lot_id.name or receipt_ml[0].lot_name
            line.batch_no = batch

    standard_batch = fields.Char(string='Standard Batch')
    manf_date = fields.Date(string='Manufacture Date')
    exp_date = fields.Date(string='Expiration Date')
    mrp = fields.Float(string='MRP')
    client_coa = fields.Many2many('ir.attachment', 'inspection_report_line_doc_attach_rel',
        'doc_id', 'attach_id', string="Attachment", copy=False,
        help='You can attach the copy of your document')
    product_sent = fields.Char(string='Product Sent')
    move_id = fields.Many2one('stock.move', string="Sample Move", readonly=True)

    ########## For packing #############
    tube = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Tube/Bottle/Jar/Pump')
    tube_remarks = fields.Char(string='Comments (if No)')
    box = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Box/Sticker')
    box_remarks = fields.Char(string='Comments (if No)')
    action_taken_packing = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Informed & Action Taken?') 

    ########## For color#############
    color = fields.Char(string='Product Color')
   
    color_standard = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Color: As per Standard')
    no_reason_color = fields.Char(string='Reason (if No)')
    action_taken_color = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Informed & Action Taken?') 

    ########## For consistency ############
    consistency_standard = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Consistency: As per Standard')
    no_reason_consistency = fields.Char(string='Reason (if No)')
    action_taken_consistency = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Informed & Action Taken?') 

    ########## For perfume ############
    perfume_standard = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Perfume: As per Standard')
    no_reason_perfume = fields.Char(string='Reason (if No)')
    action_taken_perfume = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Informed & Action Taken?') 

    ########## For spreadability ############
    spreadability_standard = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Spreadability: As per Standard')
    no_reason_spreadability = fields.Char(string='Reason (if No)')
    action_taken_spreadability = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ], string='Informed & Action Taken?') 
    
    remarks = fields.Text(string="Remarks")
    conclusion = fields.Selection([
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string="Conclusion")

    @api.model
    def create(self, vals):
        """Assign a sequence to each inspection line."""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('inspection.report.line') or 'New'
        return super(InspectionReportLine, self).create(vals)
    
    @api.depends('quantity', 'sample_quantity')
    def _compute_balance_quantity(self):
        for line in self:
            line.balance_quantity = max(line.quantity - line.sample_quantity, 0)

    def action_open_line_report(self):
        """Open dedicated inspection line form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inspection Line Details'),
            'res_model': 'inspection.report.line',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(self.env.ref('ubik_inventory.view_inspection_report_line_form_detailed').id, 'form')],
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
    inspection_date = fields.Datetime(string="Inspection Date",related="report_id.date")

class InspectionReport(models.Model):
    _name = 'inspection.report'
    _description = 'Inspection Report'

    name = fields.Char(string="Report Reference", required=True, copy=False, readonly=True, default='New')
    picking_id = fields.Many2one('stock.picking', string="Receipt", required=True)
    date = fields.Datetime(string="Inspection Date", default=fields.Datetime.now)
    inspector_id = fields.Many2one('res.users', string="Inspector", default=lambda self: self.env.user)
    inspection_line_ids = fields.One2many('inspection.report.line', 'report_id', string="Inspection Lines")
    state = fields.Selection([
        ('draft', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
    ], string="Status", default='draft', tracking=True)

    # ------------------------------
    # Button methods
    # ------------------------------
    
    def action_start_inspection(self):
        """Start inspection and create internal picking + stock moves for sample quantities."""
        for record in self:
            if not record.picking_id:
                raise ValidationError(_("No related picking found for this inspection report."))

            record.state = 'in_progress'
            picking = record.picking_id

            # --- Find or create Quality Check location ---
            quality_loc = self.env['stock.location'].search([('name', '=', 'Quality Check')], limit=1)
            if not quality_loc:
                quality_loc = self.env['stock.location'].create({
                    'name': 'Quality Check',
                    'usage': 'internal',
                    'location_id': picking.location_dest_id.id or self.env.ref('stock.stock_location_stock').id,
                })

            # --- Find Internal Picking Type ---
            internal_picking_type = self.env.ref('stock.picking_type_internal', raise_if_not_found=False)
            if not internal_picking_type:
                raise ValidationError(_("Internal Picking Type not found. Please configure it."))

            # --- Create the Internal Picking for this inspection ---
            internal_picking = self.env['stock.picking'].sudo().create({
                'picking_type_id': internal_picking_type.id,
                'location_id': picking.location_dest_id.id,
                'location_dest_id': quality_loc.id,
                'origin': record.name,
                'note': 'Auto-created for quality inspection samples',
            })

            # --- Create stock moves for each inspection line ---
            for line in record.inspection_line_ids:
                if not line.sample_quantity or line.sample_quantity <= 0:
                    continue

                product = line.product_id
                move_vals = {
                    'name': f'Sample Move for {product.display_name}',
                    'product_id': product.id,
                    'product_uom_qty': line.sample_quantity,
                    'product_uom': product.uom_id.id,
                    'picking_id': internal_picking.id,
                    'location_id': picking.location_dest_id.id,
                    'location_dest_id': quality_loc.id,
                    'origin': record.name,
                }

                move = self.env['stock.move'].sudo().create(move_vals)
                line.move_id = move.id  # link for traceability

            # --- Confirm & Assign Picking ---
            internal_picking.action_confirm()
            internal_picking.action_assign()
            # --- Create Move Lines --- old code without lot tracking:starts
            # for move in internal_picking.move_ids:
            #     if not move.move_line_ids:
            #         self.env['stock.move.line'].sudo().create({
            #             'move_id': move.id,
            #             'picking_id': internal_picking.id,
            #             'product_id': move.product_id.id,
            #             'product_uom_id': move.product_uom.id,
            #             'location_id': move.location_id.id,
            #             'location_dest_id': move.location_dest_id.id,
            #             'quantity': move.product_uom_qty, 
            #         })
            #     else:
            #         move.move_line_ids.write({'quantity': move.product_uom_qty})
            # old code without lot tracking:ends

            # --- Create Move Lines (WITH AUTO LOT ASSIGNMENT) starts ---
            for move in internal_picking.move_ids:

                # Find original receipt move line for same product
                receipt_move_line = record.picking_id.move_line_ids.filtered(
                    lambda ml: ml.product_id.id == move.product_id.id
                )[:1]

                lot_id = receipt_move_line.lot_id.id if receipt_move_line and receipt_move_line.lot_id else False
                lot_name = receipt_move_line.lot_name if receipt_move_line and receipt_move_line.lot_name else False

                create_vals = {
                    'move_id': move.id,
                    'picking_id': internal_picking.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'quantity': move.product_uom_qty,
                }

                # Insert lot/serial number
                if lot_id:
                    create_vals['lot_id'] = lot_id
                if lot_name:
                    create_vals['lot_name'] = lot_name

                if not move.move_line_ids:
                    self.env['stock.move.line'].sudo().create(create_vals)
                else:
                    move.move_line_ids.write(create_vals)

            # Create move lines (WITH AUTO LOT ASSIGNMENT): ends

            # --- Validate Picking (deducts stock) ---
            internal_picking.button_validate()

            _logger.info(f"Internal Picking {internal_picking.name} validated for inspection {record.name}")

        return True


    def action_inspection_completed(self):
        """Mark inspection as completed and move samples from QC to Retention."""
        for record in self:
            record.state = 'done'

            if not record.inspection_line_ids:
                continue

            # --- Locate QC location ---
            qc_loc = self.env['stock.location'].search([('name', '=', 'Quality Check')], limit=1)
            if not qc_loc:
                raise ValidationError(_("Quality Check location not found."))

            # --- Locate or Create Retention Location ---
            retention_loc = self.env['stock.location'].search([('name', '=', 'Retain Sample')], limit=1)
            if not retention_loc:
                retention_loc = self.env['stock.location'].create({
                    'name': 'Retain Sample',
                    'usage': 'internal',
                    'location_id': record.picking_id.location_dest_id.id,
                })

            # Internal Picking Type
            internal_type = self.env.ref('stock.picking_type_internal', raise_if_not_found=False)
            if not internal_type:
                raise ValidationError(_("Internal Picking Type not found."))

            # --- Create Internal Picking : QC → Retention ---
            picking_retention = self.env['stock.picking'].sudo().create({
                'picking_type_id': internal_type.id,
                'location_id': qc_loc.id,
                'location_dest_id': retention_loc.id,
                'origin': f"Retention Move - {record.name}",
                'note': 'Auto move of inspected samples to Retention warehouse',
            })

            # --- Create stock moves for each inspection line ---
            for line in record.inspection_line_ids.filtered(lambda l: l.sample_quantity > 0):
                move_vals = {
                    'name': f"Move to Retention - {line.product_id.display_name}",
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.sample_quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking_retention.id,
                    'location_id': qc_loc.id,
                    'location_dest_id': retention_loc.id,
                    'origin': record.name,
                }

                move = self.env['stock.move'].sudo().create(move_vals)

                # Create move lines (old code without lot tracking):starts
                # self.env['stock.move.line'].sudo().create({
                #     'move_id': move.id,
                #     'picking_id': picking_retention.id,
                #     'product_id': move.product_id.id,
                #     'product_uom_id': move.product_uom.id,
                #     'location_id': qc_loc.id,
                #     'location_dest_id': retention_loc.id,
                #     'quantity': move.product_uom_qty,
                # })
                # Create move lines (old code without lot tracking):ends

                # Below is new code with lot tracking support:starts
                # Get lot from QC move (created during start inspection)
                lot_id = False
                lot_name = False
                if line.move_id and line.move_id.move_line_ids:
                    qc_ml = line.move_id.move_line_ids[0]
                    lot_id = qc_ml.lot_id.id
                    lot_name = qc_ml.lot_name

                # Create move line with proper lot
                ml_vals = {
                    'move_id': move.id,
                    'picking_id': picking_retention.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': qc_loc.id,
                    'location_dest_id': retention_loc.id,
                    'quantity': move.product_uom_qty,
                }

                # Insert lot info (MANDATORY for tracked products)
                if lot_id:
                    ml_vals['lot_id'] = lot_id
                if lot_name:
                    ml_vals['lot_name'] = lot_name

                self.env['stock.move.line'].sudo().create(ml_vals)
                # new code with lot tracking support:ends

            # --- Confirm, assign, and validate the picking ---
            picking_retention.action_confirm()
            picking_retention.action_assign()
            picking_retention.button_validate()

        return True
    @api.model
    def create(self, vals):
        """Auto-generate inspection lines when creating the report from a picking."""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('inspection.report') or 'New'

        report = super(InspectionReport, self).create(vals)

        # Auto-create inspection lines if picking_id exists
        if report.picking_id:
            lines = []
            for move in report.picking_id.move_ids_without_package:
                lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': move.quantity or move.product_uom_qty,
                }))
            report.inspection_line_ids = lines

        return report

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        """Auto-populate inspection lines in the UI when user selects a picking."""
        if self.picking_id:
            lines = []
            for move in self.picking_id.move_ids_without_package:
                lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': move.quantity  or move.product_uom_qty,
                }))
            self.inspection_line_ids = lines
        else:
            self.inspection_line_ids = [(5, 0, 0)]

    def action_open_inspection_form(self):
        """Open the inspection line details for this report."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Inspection Line Details'),
            'res_model': 'inspection.report.line',
            'view_mode': 'list,form',
            'domain': [('report_id', '=', self.id)],
            'context': {'default_report_id': self.id},
            'target': 'current',
        }

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_inspection_report = fields.Boolean(
        string="Has Inspection Report",
        compute="_compute_has_inspection_report",
        store=False,
    )

    inspection_report_ids = fields.One2many(
        'inspection.report', 'picking_id', string="Inspection Reports"
    )

    @api.depends('inspection_report_ids')
    def _compute_has_inspection_report(self):
        """Check if at least one inspection report exists for this picking."""
        for picking in self:
            picking.has_inspection_report = bool(picking.inspection_report_ids)

    def action_create_inspection_report(self):
        """Create and open the inspection report."""
        self.ensure_one()

        # Prevent duplicates if user clicks twice quickly
        existing = self.env['inspection.report'].search(
            [('picking_id', '=', self.id)],
            limit=1
        )
        if existing:
            return {
                'name': 'Inspection Report',
                'type': 'ir.actions.act_window',
                'res_model': 'inspection.report',
                'view_mode': 'form',
                'res_id': existing.id,
                'target': 'current',
            }

        # Create a new inspection report
        report = self.env['inspection.report'].create({
            'picking_id': self.id,
        })

        return {
            'name': 'Inspection Report',
            'type': 'ir.actions.act_window',
            'res_model': 'inspection.report',
            'view_mode': 'form',
            'res_id': report.id,
            'target': 'current',
        }
    
    def action_view_inspection_reports(self):
        """Smart button action: open related inspection reports."""
        self.ensure_one()
        action = self.env.ref('ubik_inventory.action_quality_inspection_report').read()[0]
        action['domain'] = [('picking_id', '=', self.id)]
        action['context'] = {'default_picking_id': self.id}
        return action
    