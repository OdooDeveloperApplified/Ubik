from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging 
_logger=logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    def action_show_po(self):
        _logger.info("this is po button click")
        if self.move_id.state != "draft":
            raise UserError("Can not Perform this Operation, this operation only Apply on Draft State")
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Matching"),
            'res_model': 'purchase.bill.line.match',
            'domain': [
                ('partner_id', 'in', (self.partner_id | self.partner_id.commercial_partner_id).ids),
                ('company_id', '=', self.env.company.id),
                ('account_move_id', 'in', [self.move_id.id, False]),
                ('product_id', '=', self.product_id.id),
            ],
            'context': {
                'move_line_id': self.id,
                'move_id': self.move_id.id,
                'active_id': self.id,
                'active_model': 'account.move.line',
            },
            'views': [(self.env.ref('purchase.purchase_bill_line_match_tree').id, 'list')],
        }
class PurchaseBillMatch(models.Model):
    _inherit = "purchase.bill.line.match"
    def merge_po_line_to_vendor_bill(self):
            _logger.info("this is po called from matching %s", self.read())
            move_line_id = self.env.context.get('move_line_id')
            move_id = self.env.context.get('move_id')
            _logger.info("Move Line ID: %s", move_line_id)
            _logger.info("Move ID: %s", move_id)
            _logger.info("Context: %s", self.env.context)
            move_line_id = self.env.context.get('move_line_id')
            move_line = self.env['account.move.line'].browse(move_line_id)
            # ─────────────────────────────
            # :one: Validation
            # ─────────────────────────────
            products = self.mapped('product_id')
            uoms = self.mapped('product_uom_id')
            if len(products) > 1:
                raise UserError("Selected PO lines must have the same product.")
            if len(uoms) > 1:
                raise UserError("Selected PO lines must have the same Unit of Measure.")
            # ─────────────────────────────
            # :two: Process first PO line → update existing bill line
            # ─────────────────────────────
            first_po = self[0]
            remaining_pos = self[1:]
            def _get_price(po_line):
                price = po_line.product_uom_price
                if po_line.currency_id != move_line.currency_id:
                    price = po_line.currency_id._convert(
                        price,
                        move_line.currency_id,
                        move_line.company_id,
                        move_line.move_id.date or fields.Date.today(),
                    )
                return price
            move_line.with_context(check_move_validity=False).write({
                'quantity': first_po.product_uom_qty,
                'price_unit': _get_price(first_po),
                'product_uom_id': first_po.product_uom_id.id,
                'purchase_line_id': first_po.pol_id.id if first_po.pol_id else False,
            })
            # ─────────────────────────────
            # :three: Create new bill lines for remaining PO lines
            # ─────────────────────────────
            for po in remaining_pos:
                self.env['account.move.line'].with_context(
                    check_move_validity=False
                ).create({
                    'move_id': move_line.move_id.id,
                    'product_id': po.product_id.id,
                    'name': po.product_id.display_name,
                    'quantity': po.product_uom_qty,
                    'price_unit': _get_price(po),
                    'product_uom_id': po.product_uom_id.id,
                    'purchase_line_id': po.pol_id.id if po.pol_id else False,
                    'account_id': move_line.account_id.id,
                    'tax_ids': [(6, 0, move_line.tax_ids.ids)],
                })
            # ─────────────────────────────
            # :four: Log success
            # ─────────────────────────────
            _logger.info(
                "Vendor Bill %s updated: %s PO lines merged",
                move_line.move_id.id, len(self)
            )
            # REDIRECT TO VENDOR BILL
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Bill',
                'res_model': 'account.move',
                'res_id': move_line.move_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    
    