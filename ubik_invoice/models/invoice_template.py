from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    lut_arn = fields.Char(string='LUT ARN')
    ad_code = fields.Char(string='AD Code')