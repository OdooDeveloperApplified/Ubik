from odoo import fields, models, api, _
from odoo.exceptions import UserError

class ContactsTemplate(models.Model):
    _inherit = "res.partner"

    # Custom fields added to Contacts form view
    delivery_time = fields.Integer(string='Delivery Time (Days)')
    drug_license_no = fields.Char(string='Drug License No.')
    food_license_no = fields.Char(string='Food License No.')
    mode_of_transport = fields.Char(string='Mode of Transport')
    place_of_delivery = fields.Char(string='Place of Delivery')

    
    