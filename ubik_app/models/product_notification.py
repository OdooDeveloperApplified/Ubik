from odoo import models, api, _
from ..fcm_utils import send_fcm_notification

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        product = super().create(vals)

        title = "New Product Launched"
        body = f"{product.name} is now available."

        product._notify_sales_users(title, body)

        return product

    def write(self, vals):
        for product in self:

            price_changed = False
            discontinued = False
            old_price = product.list_price

            if 'list_price' in vals and vals['list_price'] != old_price:
                price_changed = True

            if 'active' in vals and vals['active'] is False:
                discontinued = True

            result = super(ProductTemplate, product).write(vals)

            # Send after write
            if price_changed:
                title = "Product Price Updated"
                body = f"{product.name} price changed from {old_price} to {product.list_price}"
                product._notify_sales_users(title, body)

            if discontinued:
                title = "Product Discontinued"
                body = f"{product.name} is no longer available."
                product._notify_sales_users(title, body)

        return result

    def _notify_sales_users(self, title, body):
        for product in self:

            users = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('ubik_app.group_sales_user').id),
                ('employee_id.product_category_ids', 'in', product.categ_id.id),
                ('device_token', '!=', False)
            ])

            # Collect unique device tokens
            tokens = set(users.mapped('device_token'))

            for token in tokens:
                send_fcm_notification(token, title, body)