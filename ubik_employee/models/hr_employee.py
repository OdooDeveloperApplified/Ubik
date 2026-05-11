from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    _inherit = "hr.employee"

    doj = fields.Date(string="Joining Date", tracking=True)
   
    ############## UBIK APP CODE:starts ###################
    ####### Old code for single territory assigned to MR in Employee module: starts ##############
    # territory_ids = fields.Many2one(
    #     'territory.name',
    #     string="Assigned Territory"
    # )
    ####### Old code for single territory assigned to MR in Employee module: ends ##############

    ###### New code for multi territories assigned to MR in Employee module: starts ##############
    territory_ids = fields.Many2many('territory.name','hr_employee_territory_rel','employee_id','territory_id',string="Assigned Territories",tracking=True)
    replacement_employee_id = fields.Many2one('hr.employee',string="Transfer Records To", tracking=True)
    def action_transfer_mr_records(self):
        for emp in self:

            if not emp.user_id:
                raise ValidationError(_("This employee is not linked to a user."))

            if not emp.replacement_employee_id:
                raise ValidationError(_("Please select a replacement employee."))

            if not emp.replacement_employee_id.user_id:
                raise ValidationError(_("Replacement employee must have a user."))

            old_user = emp.user_id
            new_user = emp.replacement_employee_id.user_id
            new_emp = emp.replacement_employee_id

            # -------------------------------------------------
            # Strict Territory Match
            # -------------------------------------------------
            if set(emp.territory_ids.ids) != set(new_emp.territory_ids.ids):
                raise ValidationError(_(
                    "Transfer not allowed.\n\n"
                    "Territories of both MRs must match exactly."
                ))

            # -------------------------------------------------
            # Strict Division Match
            # -------------------------------------------------
            if set(emp.product_category_ids.ids) != set(new_emp.product_category_ids.ids):
                raise ValidationError(_(
                    "Transfer not allowed.\n\n"
                    "Divisions of both MRs must match exactly."
                ))

            # -------------------------------------------------
            # Perform Transfer
            # -------------------------------------------------
            records = self.env['mr.doctor'].search([
                ('mr_id', '=', old_user.id)
            ])

            records.write({
                'mr_id': new_user.id
            })

            _logger.info(
                "Transferred %s MR Doctor records from %s to %s",
                len(records),
                old_user.name,
                new_user.name
            )

        return True
    ###### New code for multi territories assigned to MR in Employee module: ends ##############
    
    product_category_ids = fields.Many2many(
        'product.category',
        'hr_employee_product_category_rel',
        'hr_employee_id',
        'product_category_id',
        string="Division",
        help="Divisions allowed for this employee.",
        tracking=True
    )
    ############## UBIK APP CODE:ends ###################

    def _sync_contact_details(self):
        """
        Sync Employee Territories, PAN, Job Position, and Phone to related Contact
        """
        for emp in self:

            partner = emp.work_contact_id

            if not partner:
                continue

            vals = {}

            # Sync Territories
            if emp.territory_ids:
                vals['territory_id'] = [(6, 0, emp.territory_ids.ids)]

            # Sync PAN Number
            if hasattr(emp, 'ssnid') and emp.ssnid:
                vals['l10n_in_pan'] = emp.ssnid

            # Sync Job Position (Function/Title)
            if emp.job_id and emp.job_id.name:
                vals['function'] = emp.job_id.name
                # Also update job title if you have a custom field
                # vals['job_title'] = emp.job_id.name

            # Sync Phone Numbers
            if emp.work_phone:
                vals['phone'] = emp.work_phone
            if emp.mobile_phone:
                vals['mobile'] = emp.mobile_phone
            
            # Sync Email if needed
            if emp.work_email:
                vals['email'] = emp.work_email

            if vals:
                partner.write(vals)
                _logger.info(
                    "Synced territories, PAN, job position, and phone for employee %s to partner %s",
                    emp.name,
                    partner.name
                )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._sync_contact_details()
        return employees

    def write(self, vals):
        res = super().write(vals)

        # Check which fields were updated
        territory_changed = 'territory_ids' in vals
        pan_changed = 'ssnid' in vals
        job_changed = 'job_id' in vals
        phone_changed = 'work_phone' in vals or 'mobile_phone' in vals
        email_changed = 'work_email' in vals

        if territory_changed or pan_changed or job_changed or phone_changed or email_changed:
            self._sync_contact_details()

        return res
   
  
  