from odoo import models, fields, tools
import logging

_logger = logging.getLogger(__name__)

class MrDoctorSalesReport(models.Model):
    _name = 'mr.doctor.sales.report'
    _description = 'Doctor Wise Sales Report'
    _auto = False
    _rec_name = 'doctor_id'  # Add a rec_name for better handling

    # Remove the problematic read_group override - it's causing issues
    # The default_order in the tree view is sufficient

    # Code to delete record
    def unlink(self):
        for rec in self:
            domain = [
                ('mr_doctor_id.mr_id', '=', rec.mr_id.id),
                ('mr_doctor_id.doctor_id', '=', rec.doctor_id.id),
                ('category_id', '=', rec.category_id.id),
                ('product_id', '=', rec.product_id.id),
                ('rate_type', '=', rec.rate_type),
            ]

            lines = self.env['mr.doctor.line'].search(domain)
            lines.unlink()

        return True
    
    mr_id = fields.Many2one('res.users', string="MR Name", readonly=True)
    doctor_id = fields.Many2one('res.partner', string="Doctor Name", readonly=True)
    doc_unique_id = fields.Char(string="Doctor ID", readonly=True)
    territory_id = fields.Many2one('territory.name', string="Territory", readonly=True)
    category_id = fields.Many2one('product.category', string="Division", readonly=True)
    product_id = fields.Many2one('product.template', string="Product", readonly=True)
    rate_type = fields.Selection([
        ('ptr_rate', 'PTR Rate'),
        ('custom_rate', 'Custom Rate'),
    ], readonly=True)
    price_unit = fields.Float(string='Final Rate', readonly=True)
    year = fields.Char(string="Year", readonly=True)
    is_current_fy = fields.Boolean(readonly=True)
    apr_qty = fields.Float(readonly=True)
    apr_amt = fields.Float(readonly=True)
    may_qty = fields.Float(readonly=True)
    may_amt = fields.Float(readonly=True)
    jun_qty = fields.Float(readonly=True)
    jun_amt = fields.Float(readonly=True)
    jul_qty = fields.Float(readonly=True)
    jul_amt = fields.Float(readonly=True)
    aug_qty = fields.Float(readonly=True)
    aug_amt = fields.Float(readonly=True)
    sep_qty = fields.Float(readonly=True)
    sep_amt = fields.Float(readonly=True)
    oct_qty = fields.Float(readonly=True)
    oct_amt = fields.Float(readonly=True)
    nov_qty = fields.Float(readonly=True)
    nov_amt = fields.Float(readonly=True)
    dec_qty = fields.Float(readonly=True)
    dec_amt = fields.Float(readonly=True)
    jan_qty = fields.Float(readonly=True)
    jan_amt = fields.Float(readonly=True)
    feb_qty = fields.Float(readonly=True)
    feb_amt = fields.Float(readonly=True)
    mar_qty = fields.Float(readonly=True)
    mar_amt = fields.Float(readonly=True)

    product_qty = fields.Float(string="Total Quantity", readonly=True)
    amount = fields.Float(string="Total Amount", readonly=True)

    def init(self):
        _logger.info("CREATING VIEW mr_doctor_sales_report")
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Optimized query using CTE approach similar to your working reference
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW mr_doctor_sales_report AS (
            WITH base AS (
                SELECT
                    line.id,
                    doc.mr_id,
                    doc.doctor_id,
                    doc.territory_id,
                    rp.doc_unique_id,
                    line.category_id,
                    line.product_id,
                    line.rate_type,
                    line.price_unit,
                    
                    -- Safe numeric conversion for quantity and amount
                    COALESCE(NULLIF(line.product_qty::text, 'NaN')::numeric, 0) AS product_qty,
                    COALESCE(NULLIF(line.amount::text, 'NaN')::numeric, 0) AS amount,
                    
                    -- Precompute date
                    TO_DATE(line.month, 'YYYY-MM') AS month_date
                    
                FROM mr_doctor_line line
                INNER JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
                INNER JOIN res_partner rp ON rp.id = doc.doctor_id
                WHERE line.product_qty IS NOT NULL  -- Filter out null rows for performance
            ),
            
            final AS (
                SELECT
                    *,
                    EXTRACT(MONTH FROM month_date) AS month_num,
                    
                    CASE
                        WHEN EXTRACT(MONTH FROM month_date) >= 4
                            THEN EXTRACT(YEAR FROM month_date)
                        ELSE EXTRACT(YEAR FROM month_date) - 1
                    END AS fy_start
                    
                FROM base
            )
            
            SELECT
                MIN(id) AS id,
                mr_id,
                doctor_id,
                territory_id,
                doc_unique_id,
                category_id,
                product_id,
                rate_type,
                price_unit,
                
                -- Financial Year
                fy_start::TEXT || '-' || RIGHT((fy_start + 1)::TEXT, 2) AS year,
                
                -- Current FY flag
                (
                    fy_start =
                    CASE
                        WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                            THEN EXTRACT(YEAR FROM CURRENT_DATE)
                        ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                    END
                ) AS is_current_fy,
                
                -- Monthly Quantities
                SUM(CASE WHEN month_num = 4 THEN product_qty ELSE 0 END) AS apr_qty,
                SUM(CASE WHEN month_num = 5 THEN product_qty ELSE 0 END) AS may_qty,
                SUM(CASE WHEN month_num = 6 THEN product_qty ELSE 0 END) AS jun_qty,
                SUM(CASE WHEN month_num = 7 THEN product_qty ELSE 0 END) AS jul_qty,
                SUM(CASE WHEN month_num = 8 THEN product_qty ELSE 0 END) AS aug_qty,
                SUM(CASE WHEN month_num = 9 THEN product_qty ELSE 0 END) AS sep_qty,
                SUM(CASE WHEN month_num = 10 THEN product_qty ELSE 0 END) AS oct_qty,
                SUM(CASE WHEN month_num = 11 THEN product_qty ELSE 0 END) AS nov_qty,
                SUM(CASE WHEN month_num = 12 THEN product_qty ELSE 0 END) AS dec_qty,
                SUM(CASE WHEN month_num = 1 THEN product_qty ELSE 0 END) AS jan_qty,
                SUM(CASE WHEN month_num = 2 THEN product_qty ELSE 0 END) AS feb_qty,
                SUM(CASE WHEN month_num = 3 THEN product_qty ELSE 0 END) AS mar_qty,
                
                -- Monthly Amounts
                SUM(CASE WHEN month_num = 4 THEN amount ELSE 0 END) AS apr_amt,
                SUM(CASE WHEN month_num = 5 THEN amount ELSE 0 END) AS may_amt,
                SUM(CASE WHEN month_num = 6 THEN amount ELSE 0 END) AS jun_amt,
                SUM(CASE WHEN month_num = 7 THEN amount ELSE 0 END) AS jul_amt,
                SUM(CASE WHEN month_num = 8 THEN amount ELSE 0 END) AS aug_amt,
                SUM(CASE WHEN month_num = 9 THEN amount ELSE 0 END) AS sep_amt,
                SUM(CASE WHEN month_num = 10 THEN amount ELSE 0 END) AS oct_amt,
                SUM(CASE WHEN month_num = 11 THEN amount ELSE 0 END) AS nov_amt,
                SUM(CASE WHEN month_num = 12 THEN amount ELSE 0 END) AS dec_amt,
                SUM(CASE WHEN month_num = 1 THEN amount ELSE 0 END) AS jan_amt,
                SUM(CASE WHEN month_num = 2 THEN amount ELSE 0 END) AS feb_amt,
                SUM(CASE WHEN month_num = 3 THEN amount ELSE 0 END) AS mar_amt,
                
                -- Totals
                SUM(product_qty) AS product_qty,
                SUM(amount) AS amount
                
            FROM final
            GROUP BY
                mr_id,
                doctor_id,
                territory_id,
                doc_unique_id,
                category_id,
                product_id,
                rate_type,
                price_unit,
                fy_start
        )
        """)