from odoo import fields, models, api, _
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = "crm.lead"

    # Custom fields added to Contacts form view
    clinic_type = fields.Char(string="Clinic Type")
    requirements = fields.Html(string="Requirements")
    
    