from odoo import models, fields, tools
import logging
_logger = logging.getLogger(__name__)

class DoctorCategorySalesReport(models.Model):
    _name = 'doctor.division.sales.report'
    _description = 'Doctor Wise Category Sales Report'
    _auto = False
    _rec_name = 'category_id'

    mr_id = fields.Many2one('res.users', string="MR Name", readonly=True)
    doctor_id = fields.Many2one('res.partner', string="Doctor Name", readonly=True)
    doc_unique_id = fields.Char(string="Doctor ID", readonly=True)
    territory_id = fields.Many2one('territory.name', readonly=True)
    category_id = fields.Many2one('product.category', string="Division", readonly=True)
    year = fields.Char(readonly=True)
    is_current_fy = fields.Boolean(readonly=True)

    apr_amt = fields.Float(string="April", readonly=True)
    may_amt = fields.Float(string="May",readonly=True)
    jun_amt = fields.Float(string="June",readonly=True)
    jul_amt = fields.Float(string="July",readonly=True)
    aug_amt = fields.Float(string="August",readonly=True)
    sep_amt = fields.Float(string="September",readonly=True)
    oct_amt = fields.Float(string="October",readonly=True)
    nov_amt = fields.Float(string="November",readonly=True)
    dec_amt = fields.Float(string="December",readonly=True)
    jan_amt = fields.Float(string="January",readonly=True)
    feb_amt = fields.Float(string="February",readonly=True)
    mar_amt = fields.Float(string="March",readonly=True)

    amount = fields.Float(string="Grand Total", readonly=True)

    def init(self):
        # raise Exception("INIT IS RUNNING")
        _logger.info("CREATING VIEW doctor_division_sales_report")
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""

        CREATE OR REPLACE VIEW doctor_division_sales_report AS (

        WITH base AS (
            SELECT
                line.id,
                doc.mr_id,
                doc.doctor_id,
                doc.territory_id,
                rp.doc_unique_id,
                line.category_id,

                -- Safe amount
                COALESCE(NULLIF(line.amount::text, 'NaN')::numeric, 0) AS amount,

                -- Precompute date
                TO_DATE(line.month, 'YYYY-MM') AS month_date

            FROM mr_doctor_line line
            JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
            JOIN res_partner rp ON rp.id = doc.doctor_id
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

            -- FY
            fy_start::text || '-' || RIGHT((fy_start + 1)::text, 2) AS year,

            -- Current FY
            (
                fy_start =
                CASE
                    WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                        THEN EXTRACT(YEAR FROM CURRENT_DATE)
                    ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                END
            ) AS is_current_fy,

            -- Monthly
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

            SUM(amount) AS amount

        FROM final

        GROUP BY
            mr_id,
            doctor_id,
            territory_id,
            doc_unique_id,
            category_id,
            fy_start

        )
        """)