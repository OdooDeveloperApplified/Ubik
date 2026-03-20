from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)
    
class MrDoctor(models.Model):
    _name = 'mr.doctor'
    _description = 'MR Doctor Workflow'
    _inherit = ['mail.thread']
    _order = "create_date desc"

    # Code to give sequence to MR Doctor visit record
    name = fields.Char(string="Reference",readonly=True,copy=False,default='New')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('mr.doctor') or 'New'
        return super(MrDoctor, self).create(vals)
    
    mr_id = fields.Many2one('res.users', string="User", tracking=True)
    doctor_id = fields.Many2one('res.partner', string="Doctor", tracking=True,  domain="[('is_doctor','=',True), ('territory_id','=', territory_id)]")
    doc_unique_id = fields.Char(string="Doctor ID", readonly=True,tracking=True)
    line_ids = fields.One2many('mr.doctor.line','mr_doctor_id', string="Sales Details")

    # New code to allow multi territories for MR and restrict doctor selection based on those territories. Territory assigned to MR is fetched from Employee module based on the logged in user.
    territory_id = fields.Many2one('territory.name', string="Territory", tracking=True)
    allowed_territory_ids = fields.Many2many('territory.name',compute='_compute_allowed_territories',store=False)
    # New code to allow multi territories for MR and restrict doctor selection ends here

    ################## New code for multi territories for MR starts here ##################
    @api.depends('mr_id')
    def _compute_allowed_territories(self):
        for rec in self:
            employee = self.env['hr.employee'].sudo().search(
                [('user_id', '=', rec.mr_id.id)],
                limit=1
            )
            rec.allowed_territory_ids = employee.territory_ids if employee else False
    @api.onchange('mr_id')
    def _onchange_mr_id(self):
        return {
            'domain': {
                'territory_id': [('id', 'in', self.allowed_territory_ids.ids)]
            }
        }
    ################# New code for multi territories for MR ends here ##################
     
    # Code to populate doctor unique id assigned
    @api.onchange('doctor_id')
    def _onchange_doctor_id(self):
        for rec in self:
            rec.doc_unique_id = rec.doctor_id.doc_unique_id if rec.doctor_id else False
    
    ################## ASM Verification flow starts ################################

    job_id = fields.Many2one('hr.job',string="Job Position",compute="_compute_job_id",store=True,readonly=True,tracking=True)

    @api.depends('mr_id')
    def _compute_job_id(self):
        for rec in self:
            rec.job_id = False

            if not rec.mr_id:
                continue

            employee = rec.mr_id.employee_id

            if employee and employee.job_id:
                rec.job_id = employee.job_id

    asm_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='draft', string="Status", tracking=True)


    manager_id = fields.Many2one('res.users',string="Manager",compute="_compute_manager_id",store=True,tracking=True)

    @api.depends('mr_id')
    def _compute_manager_id(self):
        for rec in self:
            rec.manager_id = False

            if not rec.mr_id:
                continue

            employee = rec.mr_id.employee_id 

            if employee and employee.parent_id and employee.parent_id.user_id:
                rec.manager_id = employee.parent_id.user_id

    def action_submit_to_asm(self):
        for rec in self:
            if not rec.manager_id:
                raise UserError(_("No Manager defined for this user."))

            rec.asm_state = 'submitted'

            # Notify ASM in chatter
            rec.message_post(
                body=_("Record submitted for ASM verification."),
                partner_ids=[rec.manager_id.partner_id.id]
            )
    
    def action_verify_by_asm(self):
        for rec in self:
            if self.env.user != rec.manager_id:
                raise UserError(_("Only assigned Manager can verify this record."))
            rec.asm_state = 'verified'

    def action_reject_by_asm(self):
        for rec in self:
            if self.env.user != rec.manager_id:
                raise UserError(_("Only assigned Manager can reject this record."))
            rec.asm_state = 'rejected'
    
    rejection_reason = fields.Text(string="Rejection Reason", tracking=True)

    record_save = fields.Boolean(string="Record Save", compute="_compute_record_save",store=True)

    @api.depends('unlock_for_edit', 'create_date')
    def _compute_record_save(self):

        today = datetime.today()
        current_year = today.year
        current_month = today.month

        for rec in self:
            if rec.unlock_for_edit:
                rec.record_save = False
                continue

            if not rec.create_date:
                rec.record_save = False
                continue

            create_year = rec.create_date.year
            create_month = rec.create_date.month

            if (create_year < current_year) or (
                create_year == current_year and create_month < current_month
            ):
                rec.record_save = True
            else:
                rec.record_save = False

    unlock_for_edit = fields.Boolean(string="Unlocked by Admin", default=False)
    unlocked_by = fields.Many2one('res.users', string="Unlocked By", readonly=True)

    # Add these new fields for bulk operation tracking
    bulk_unlock_id = fields.Char(string="Bulk Unlock Reference", readonly=True, copy=False)
    bulk_unlocked_by = fields.Many2one('res.users', string="Bulk Unlocked By", readonly=True)
    bulk_unlock_date = fields.Datetime(string="Bulk Unlock Date", readonly=True)

    original_asm_state = fields.Selection([
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
    ], string="Original Status", readonly=True, copy=False)

    was_edited_after_unlock = fields.Boolean(
        string="Was Edited After Unlock",
        default=False,
        help="Technical field to track if record was modified after being unlocked"
    )

    def action_unlock_record(self):
        for rec in self:
            if not self.env.user.has_group('base.group_system'):
                raise UserError(_("Only Admin can unlock past month records."))

            if not rec.record_save:
                raise UserError(_("Only past month records can be unlocked."))
            original_state = rec.asm_state 
            rec.write({
                'original_asm_state': original_state,
                'unlock_for_edit': True,
                'unlocked_by': self.env.user.id,
                'asm_state': 'draft',
                'was_edited_after_unlock': False, 
                
            })

    def action_lock_after_edit(self):
            for rec in self:
                # Only Admin can lock
                if not self.env.user.has_group('base.group_system'):
                    raise UserError(_("Only Admin can lock this record."))

                was_edited = rec.was_edited_after_unlock
                original_state = rec.original_asm_state
                current_state = rec.asm_state

                if not was_edited:
                    new_state = original_state or 'draft'
                else:
                    if current_state in ['verified', 'rejected']:
                        new_state = current_state
                    else:
                        new_state = 'submitted'

                rec.write({
                    'unlock_for_edit': False,
                    'asm_state': new_state,
                    'original_asm_state': False,
                })
                # Force recompute of record_save
            rec._compute_record_save()

    def write(self, vals):
        for rec in self:
            # Detect REAL user edit only (very strict)
            is_real_edit = (
                rec.unlock_for_edit
                and not self.env.user.has_group('base.group_system')
                and not self.env.user.has_group('ubik_app.group_sales_manager')
            )

            # Fields that indicate SYSTEM operations (LOCK/UNLOCK)
            system_fields = {
                'unlock_for_edit',
                'asm_state',
                'original_asm_state',
                'was_edited_after_unlock',
                'unlocked_by',
                'bulk_unlock_id',
                'bulk_unlocked_by',
                'bulk_unlock_date',
            }

            # Only mark edited if USER changes BUSINESS fields
            if is_real_edit:
                edited_fields = set(vals.keys()) - system_fields

                if edited_fields:
                    vals['was_edited_after_unlock'] = True
                    
                    # If the record is being edited, ensure it's set to draft
                    # This allows it to be submitted again
                    if rec.asm_state in ['verified', 'rejected']:
                        vals['asm_state'] = 'draft'

            # Admin bypass
            if self.env.user.has_group('base.group_system'):
                continue

            # Prevent editing locked records
            if rec.record_save and not rec.unlock_for_edit:
                raise UserError(_("Past month records are locked. Contact Admin."))

        return super().write(vals)

    def _cron_auto_lock_past_month_records(self):
        today = datetime.today()
        current_year = today.year
        current_month = today.month

        records = self.search([
            ('unlock_for_edit', '=', False)
        ])

        for rec in records:
            if not rec.create_date:
                continue

            create_year = rec.create_date.year
            create_month = rec.create_date.month

            # If record is from past month (or past year)
            if (create_year < current_year) or \
            (create_year == current_year and create_month < current_month):

                rec.record_save = True
    
    class MrDoctorRejectWizard(models.TransientModel):
        _name = 'mr.doctor.reject.wizard'
        _description = 'MR Doctor Reject Wizard'

        reason = fields.Text(string="Comment", required=True)

        def action_confirm_reject(self):
            active_id = self.env.context.get('active_id')
            record = self.env['mr.doctor'].browse(active_id)

            if not record:
                return

            # Security check (same as your logic)
            if self.env.user != record.manager_id and not self.env.user.has_group('base.group_system'):
                raise UserError(_("Only assigned Manager can reject this record."))

            record.write({
                'asm_state': 'rejected',
                'rejection_reason': self.reason
            })

            record.message_post(
                body=_("Record rejected.Reason:%s") % self.reason
            )

            return {'type': 'ir.actions.act_window_close'}
    
    ################## ASM Verification flow ends ################################

class MrDoctorLine(models.Model):
    _name = 'mr.doctor.line'
    _description = 'MR Doctor Sales Line'
    _inherit = ['mail.thread']

    mr_doctor_id = fields.Many2one('mr.doctor',string="MR Doctor")

    allowed_category_ids = fields.Many2many('product.category',compute='_compute_allowed_categories',store=False)

    category_id = fields.Many2one('product.category',string="Division",tracking=True,domain="[('id', 'in', allowed_category_ids)]")

    product_id = fields.Many2one('product.template',string="Product",domain="[('sale_ok','=',True), ('categ_id','=',category_id), ('id','in', allowed_product_ids)]", tracking=True)

    allowed_product_ids = fields.Many2many(
        'product.template', 
        compute='_compute_allowed_products', 
        store=False
    )
    # Code to populate the categories (Division) assigned to MR in Employee Module
    @api.depends('mr_doctor_id.mr_id')
    def _compute_allowed_categories(self):
        for line in self:
            line.allowed_category_ids = False
            if not line.mr_doctor_id or not line.mr_doctor_id.mr_id:
                continue

            employee = self.env['hr.employee'].sudo().search(
                [('user_id', '=', line.mr_doctor_id.mr_id.id)],
                limit=1
            )

            if employee and employee.product_category_ids:
                line.allowed_category_ids = employee.product_category_ids
    
    @api.depends('category_id', 'mr_doctor_id.territory_id')
    def _compute_allowed_products(self):
        for line in self:
            line.allowed_product_ids = False
            
            if not line.category_id or not line.mr_doctor_id or not line.mr_doctor_id.territory_id:
                continue
            
            # Base domain: sale_ok=True and selected category
            domain = [
                ('sale_ok', '=', True),
                ('categ_id', '=', line.category_id.id)
            ]
            
            # Get all products matching base criteria
            products = self.env['product.template'].search(domain)
            
            # Filter products based on territory
            allowed_products = self.env['product.template']
            
            for product in products:
                # If product is territory specific, check if current territory is allowed
                if product.is_territory_specific_product:
                    if line.mr_doctor_id.territory_id in product.allowed_territory_ids:
                        allowed_products |= product
                else:
                    # If product is not territory specific, include it
                    allowed_products |= product
            
            line.allowed_product_ids = allowed_products

    # Code to clear the product lines if the Division is changed
    @api.onchange('category_id')
    def _onchange_category_id(self):
        for line in self:
            # Clear dependent fields
            line.product_id = False
            line.rate_type = False
            line.price_unit = 0.0
            line.product_qty = 1.0
            line.amount = 0.0
            line.ptr_rate = 0.0
            line.custom_rate = 0.0

            if line.category_id and line.mr_doctor_id and line.mr_doctor_id.territory_id:
                # Compute allowed products
                line._compute_allowed_products()
                
                return {
                    'domain': {
                        'product_id': [
                            ('sale_ok', '=', True),
                            ('categ_id', '=', line.category_id.id),
                            ('id', 'in', line.allowed_product_ids.ids)
                        ]
                    }
                }

    # Code to add month field in product lines, which displays the current month and year
    def _get_month_year_selection(self):
        selection = []
        start = datetime.today().replace(day=1)
        
        # generate last 1 month + next 12 months 
        for i in range(-24, 24):
            dt = start + relativedelta(months=i)
            key = dt.strftime('%Y-%m')          # stored value
            label = dt.strftime('%b %Y')        # shown to user (Dec 2025)
            selection.append((key, label))
        return selection
    
    month = fields.Selection(selection=_get_month_year_selection,string="Month",default=lambda self: datetime.today().strftime('%Y-%m'),
    required=True, tracking=True)

    rate_type = fields.Selection([
        ('ptr_rate', 'PTR Rate'),
        ('custom_rate', 'Custom Rate'),
    ], tracking=True)
    ptr_rate = fields.Float(string='PTR Rate', tracking=True)
    custom_rate = fields.Float(string='Custom Rate', tracking=True)

    # Code to add functionality to rate type (IF rate type=ptr rate, unit price = list price, 
    # if rate type=custom rate, unit price=0.0 and user can add desired price but less than list price)
    @api.onchange('rate_type')
    def _onchange_rate_type(self):
        for line in self:
            if line.rate_type == 'custom_rate':
                line.price_unit = 0.0

            elif line.rate_type == 'ptr_rate' and line.product_id:
                line.price_unit = line.product_id.list_price

    price_unit = fields.Float(string="Unit Price", tracking=True)
    product_qty = fields.Float(string="Quantity", default='1.0', tracking=True)
    amount = fields.Float(string="Amount",compute="_compute_amount",store=True, tracking=True)
    
    # Code to calculate amount
    @api.depends('price_unit', 'product_qty')
    def _compute_amount(self):
        for line in self:
            line.amount = line.price_unit * line.product_qty

    ############ New ASM workflow code to add discount % column under sales details starts ##############
    discount_percent = fields.Float(string="Discount %",compute="_compute_discount_percent", store=True, tracking=True)
    @api.depends('rate_type', 'price_unit', 'product_id')
    def _compute_discount_percent(self):
        for line in self:
            line.discount_percent = 0.0

            if (
                line.rate_type == 'custom_rate'
                and line.product_id
                and line.product_id.list_price > 0
            ):
                list_price = line.product_id.list_price

                line.discount_percent = (
                    (list_price - line.price_unit) / list_price
                ) * 100
    ############ New ASM workflow code to add discount % column under sales details ends ##############   

    # Code to add validation that custom price cannot be more than list price
    @api.constrains('rate_type', 'price_unit', 'product_id')
    def _check_custom_price_not_exceed_list_price(self):
        for line in self:
            if (
                line.rate_type == 'custom_rate'
                and line.product_id
                and line.price_unit > line.product_id.list_price
            ):
                raise UserError(_(
                    "Custom price (%s) cannot be greater than the product list price (%s) for product '%s'."
                ) % (
                    line.price_unit,
                    line.product_id.list_price,
                    line.product_id.display_name
                ))

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_territory_specific_product = fields.Boolean(
        string="Territory Specific Product",
        help="If enabled, product will be visible only to selected territories."
    )

    allowed_territory_ids = fields.Many2many(
        'territory.name',
        string="Allowed Territories"
    )

class MrDoctorBulkLockWizard(models.TransientModel):
    _name = 'mr.doctor.bulk.lock.wizard'
    _description = 'MR Doctor Bulk Lock/Unlock Wizard'

    user_id = fields.Many2one('res.users', string="MR User", required=True,
                               domain="[('share', '=', False)]")
    doctor_id = fields.Many2one('res.partner', string="Doctor", 
                                domain="[('is_doctor','=',True)]")
    category_id = fields.Many2one('product.category', string="Division")
    month = fields.Selection(
        selection='_get_month_year_selection',
        string="Month",
        required=True
    )
    
    operation_type = fields.Selection([
        ('unlock', 'Unlock Records'),
        ('lock', 'Lock Records'),
    ], string="Operation", required=True, default='unlock')
    
    record_count = fields.Integer(string="Records to Process", compute='_compute_record_count')

    # New fields to store allowed doctors and categories for the selected MR
    allowed_doctor_ids = fields.Many2many('res.partner', compute='_compute_allowed_doctors', store=False)
    allowed_category_ids = fields.Many2many('product.category', compute='_compute_allowed_categories', store=False)
    
    def _get_month_year_selection(self):
        """Generate month-year selection for last 24 months"""
        selection = []
        today = datetime.today()
        for i in range(-12, 1):  # Last 24 months up to current month
            dt = today.replace(day=1) + relativedelta(months=i)
            key = dt.strftime('%Y-%m')
            label = dt.strftime('%b %Y')
            selection.append((key, label))
        return selection
    
    @api.depends('user_id')
    def _compute_allowed_doctors(self):
        """Compute doctors that the selected MR has visited"""
        for wizard in self:
            wizard.allowed_doctor_ids = False
            if not wizard.user_id:
                continue
            
            # Find all mr.doctor records for this user
            mr_doctor_records = self.env['mr.doctor'].sudo().search([
                ('mr_id', '=', wizard.user_id.id)
            ])
            
            # Get unique doctor IDs from those records
            if mr_doctor_records:
                wizard.allowed_doctor_ids = mr_doctor_records.mapped('doctor_id')
    
    @api.depends('user_id')
    def _compute_allowed_categories(self):
        """Compute categories (divisions) assigned to the MR in Employee module"""
        for wizard in self:
            wizard.allowed_category_ids = False
            if not wizard.user_id:
                continue
            
            # Find employee linked to this user
            employee = self.env['hr.employee'].sudo().search([
                ('user_id', '=', wizard.user_id.id)
            ], limit=1)
            
            if employee and employee.product_category_ids:
                wizard.allowed_category_ids = employee.product_category_ids
    
    @api.onchange('user_id')
    def _onchange_user_id(self):
        """Update domains for doctor_id and category_id based on selected MR"""
        if self.user_id:
            # Force recompute of allowed fields
            self._compute_allowed_doctors()
            self._compute_allowed_categories()
            
            return {
                'domain': {
                    'doctor_id': [
                        ('is_doctor', '=', True),
                        ('id', 'in', self.allowed_doctor_ids.ids)
                    ],
                    'category_id': [
                        ('id', 'in', self.allowed_category_ids.ids)
                    ]
                }
            }
        else:
            # Reset domains when no user selected
            return {
                'domain': {
                    'doctor_id': [('is_doctor', '=', True)],
                    'category_id': []
                }
            }
    
    @api.depends('user_id', 'doctor_id', 'category_id', 'month')
    def _compute_record_count(self):
        """Count records that will be affected by the operation"""
        for wizard in self:
            if not wizard.user_id or not wizard.month:
                wizard.record_count = 0
                continue
                
            domain = wizard._get_record_domain()
             # If category is specified, we need to check line records
            if wizard.category_id:
                # Find mr.doctor records that have at least one line with this category
                line_domain = [
                    ('mr_doctor_id.mr_id', '=', wizard.user_id.id),
                    ('mr_doctor_id.create_date', '>=', wizard._get_month_start(wizard.month)),
                    ('mr_doctor_id.create_date', '<=', wizard._get_month_end(wizard.month)),
                    ('category_id', '=', wizard.category_id.id)
                ]
                
                if wizard.doctor_id:
                    line_domain.append(('mr_doctor_id.doctor_id', '=', wizard.doctor_id.id))
                
                # Get distinct mr_doctor_ids from lines
                lines = self.env['mr.doctor.line'].sudo().search(line_domain)
                mr_doctor_ids = lines.mapped('mr_doctor_id').ids
                wizard.record_count = len(mr_doctor_ids)
            else:
                # Original count logic without category filter
                wizard.record_count = self.env['mr.doctor'].sudo().search_count(domain)
    
    def _get_record_domain(self):
        """Build domain for finding records to process"""
        domain = [
            ('mr_id', '=', self.user_id.id),
            ('create_date', '>=', self._get_month_start(self.month)),
            ('create_date', '<=', self._get_month_end(self.month)),
        ]
        
        if self.doctor_id:
            domain.append(('doctor_id', '=', self.doctor_id.id))
            
        return domain
    
    def _get_month_start(self, month_str):
        """Convert month string (YYYY-MM) to datetime start of month"""
        year, month = map(int, month_str.split('-'))
        return datetime(year, month, 1, 0, 0, 0)
    
    def _get_month_end(self, month_str):
        """Convert month string (YYYY-MM) to datetime end of month"""
        year, month = map(int, month_str.split('-'))
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return next_month - timedelta(seconds=1)
    
    def _get_filtered_records(self):
        """Get records filtered by all criteria including category if specified"""
        if not self.category_id:
            # No category filter, return all records matching base domain
            domain = self._get_record_domain()
            return self.env['mr.doctor'].sudo().search(domain)
        
        # Category filter applied - find mr.doctor records that have at least one line with this category
        line_domain = [
            ('mr_doctor_id.mr_id', '=', self.user_id.id),
            ('mr_doctor_id.create_date', '>=', self._get_month_start(self.month)),
            ('mr_doctor_id.create_date', '<=', self._get_month_end(self.month)),
            ('category_id', '=', self.category_id.id)
        ]
        
        if self.doctor_id:
            line_domain.append(('mr_doctor_id.doctor_id', '=', self.doctor_id.id))
        
        lines = self.env['mr.doctor.line'].sudo().search(line_domain)
        return lines.mapped('mr_doctor_id')
    
    def action_process_bulk_lock(self):
        """Process bulk lock/unlock operation"""
        self.ensure_one()
        
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only Admin can perform bulk lock/unlock operations."))
        
        if self.record_count == 0:
            raise UserError(_("No records found matching the criteria."))
        
        # Get records to process
        records = self._get_filtered_records()
        
        if not records:
            raise UserError(_("No records found matching the criteria."))
        
        # Generate bulk operation reference
        bulk_ref = f"BULK-{self.operation_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self.env.user.id}"
        
        # ===================== UNLOCK =====================
        if self.operation_type == 'unlock':
            
            for record in records:
                original_state = record.asm_state

                record.write({
                    'original_asm_state': original_state,
                    'unlock_for_edit': True,
                    'unlocked_by': self.env.user.id,
                    'asm_state': 'draft',
                    'bulk_unlock_id': bulk_ref,
                    'bulk_unlocked_by': self.env.user.id,
                    'bulk_unlock_date': fields.Datetime.now(),
                    'was_edited_after_unlock': False,
                })

            for record in records:
                doctor_info = f"for Dr. {record.doctor_id.name}" if record.doctor_id else ""
                category_info = f" (Division: {self.category_id.name})" if self.category_id else ""

                record.message_post(
                    body=_("Record bulk unlocked by Admin %s  %s%s. Original state: %s") % (
                        self.env.user.name,
                        
                        doctor_info,
                        category_info,
                        record.original_asm_state
                    )
                )

            category_text = f" in division {self.category_id.name}" if self.category_id else ""

            message = _("%s records have been successfully unlocked for %s in %s%s. Original states preserved.") % (
                len(records),
                self.user_id.name,
                self.month,
                category_text
            )

            # Return action that closes wizard and shows notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Bulk Unlock Successful'),
                    'message': message,
                    'sticky': False,
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    }
                }
            }

        # ===================== LOCK =====================
        else:
            records = records.filtered(lambda r: r.unlock_for_edit)

            if not records:
                raise UserError(_("No unlocked records found for the given criteria."))

            edited_count = 0
            restored_count = 0

            for record in records:

                # Check if record was edited OR if it's in a non-draft state that wasn't its original state
                was_edited = record.was_edited_after_unlock
                original_state = record.original_asm_state
                current_state = record.asm_state

                _logger.info(
                    "Processing record %s: edited=%s original=%s current=%s",
                    record.id, was_edited, original_state, current_state
                )

                # FIX: Also consider a record as "edited" if it reached a verified/rejected state
                # that's different from its original state
                if not was_edited and current_state in ['verified', 'rejected']:
                    # Check if the current state is different from original
                    if current_state != original_state:
                        was_edited = True
                        _logger.info("Record %s marked as edited because it reached %s state", 
                                    record.id, current_state)

                # DECIDE STATE BASED ON THE FIXED was_edited FLAG
                if not was_edited:
                    new_state = original_state or 'draft'
                    restored_count += 1
                else:
                    # If edited, keep the current state (whether verified, rejected, or submitted)
                    if current_state in ['verified', 'rejected']:
                        new_state = current_state
                    else:
                        # If it's in draft/submitted and was edited, send for verification
                        new_state = 'submitted'
                    edited_count += 1

                # APPLY WRITE
                record.write({
                    'unlock_for_edit': False,
                    'asm_state': new_state,
                    'original_asm_state': False,
                })

                # MESSAGE
                doctor_info = f"for Dr. {record.doctor_id.name}" if record.doctor_id else ""
                category_info = f" (Division: {self.category_id.name})" if self.category_id else ""

                if was_edited:
                    msg = f"Edited - {'kept verified state' if new_state == 'verified' else 'sent for re-verification'}"
                else:
                    msg = f"Restored to original state: {original_state}"

                record.message_post(
                    body=_("Record bulk locked by Admin %s  %s%s. %s") % (
                        self.env.user.name,
                    
                        doctor_info,
                        category_info,
                        msg
                    )
                )

            # FINAL MESSAGE
            category_text = f" in division {self.category_id.name}" if self.category_id else ""

            message = _(
                "%s records locked (%s edited → %s, %s restored)%s"
            ) % (
                len(records),
                edited_count,
                "kept verified state" if any(r.asm_state == 'verified' for r in records.filtered(lambda x: x.was_edited_after_unlock)) else "sent for re-verification",
                restored_count,
                category_text
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Bulk Lock Successful'),
                    'message': message,
                    'sticky': False,
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    }
                }
            }