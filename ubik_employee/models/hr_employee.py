from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    _inherit = "hr.employee"

    doj = fields.Date(string="Joining Date")


  
  