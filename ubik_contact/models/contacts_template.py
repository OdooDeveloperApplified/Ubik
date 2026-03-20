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

    ########## UBIK APP CODE STARTS ##############
    is_doctor = fields.Boolean(string="Is Doctor")
    territory_id = fields.Many2one('territory.name',string='Territory')
    doc_unique_id = fields.Char(string='Doctor ID')
    ########## UBIK APP CODE ENDS ##############

class TerritoryName(models.Model):
    _name = 'territory.name'
    _description = 'Create Territory Names'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name")

    
    