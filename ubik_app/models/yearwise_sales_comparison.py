from odoo import models, fields, tools

class MrDoctorAvgSalesReport(models.Model):
    _name = 'mr.doctor.avg.sales.report'
    _description = 'Doctor Avg Sales Comparison (FY)'
    _auto = False

    territory_id = fields.Many2one('territory.name', string="Territory", readonly=True)
    doctor_id = fields.Many2one('res.partner', string="Doctor Name", readonly=True)
    doc_unique_id = fields.Char(string="Doctor ID", readonly=True)
    fiscal_year = fields.Char(string="Fiscal Year", readonly=True)
    is_current_fy = fields.Boolean()

    prev_total = fields.Float(string="Total Sale Upto Prev FY", readonly=True)
    curr_total = fields.Float(string="Total Sale Upto Curr FY", readonly=True)

    prev_avg = fields.Float(string="Avg Sale Prev FY", readonly=True)
    curr_avg = fields.Float(string="Avg Sale Curr FY", readonly=True)

    total_diff = fields.Float(string="Difference (Total)", readonly=True)
    avg_diff = fields.Float(string="Difference (Avg)", readonly=True)
    pct_change = fields.Float(string="% Change", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mr_doctor_avg_sales_report AS (

                WITH params AS (
                    SELECT
                        CASE
                            WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                THEN EXTRACT(YEAR FROM CURRENT_DATE)
                            ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                        END AS curr_fy_start,

                        CASE
                            WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                THEN EXTRACT(MONTH FROM CURRENT_DATE)
                            ELSE EXTRACT(MONTH FROM CURRENT_DATE) + 12
                        END - 3 AS month_count
                ),

                sales AS (
                    SELECT
                        doc.territory_id,
                        doc.doctor_id,
                        rp.doc_unique_id,
                        line.amount,

                        CASE
                            WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM TO_DATE(line.month,'YYYY-MM'))
                            ELSE EXTRACT(YEAR FROM TO_DATE(line.month,'YYYY-MM')) - 1
                        END AS fy_year
                    FROM mr_doctor_line line
                    JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
                    JOIN res_partner rp ON rp.id = doc.doctor_id
                ),

                fy_base AS (
                    SELECT DISTINCT
                        territory_id,
                        doctor_id,
                        doc_unique_id,
                        fy_year
                    FROM sales
                )

                SELECT
                    row_number() OVER () AS id,
                    b.territory_id,
                    b.doctor_id,
                    b.doc_unique_id,
                    CONCAT(b.fy_year, '-', RIGHT((b.fy_year + 1)::text, 2)) AS fiscal_year,
                    
                    (b.fy_year = p.curr_fy_start) AS is_current_fy,

                    /* PREVIOUS FY TOTAL */
                    SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END) AS prev_total,

                    /* CURRENT FY TOTAL */
                    SUM(CASE WHEN s.fy_year = b.fy_year THEN s.amount ELSE 0 END) AS curr_total,

                    /* PREVIOUS FY AVG (ONLY FOR CURRENT FY ROW) */
                    CASE
                        WHEN b.fy_year = p.curr_fy_start
                        THEN
                            SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END)
                            / NULLIF(p.month_count, 0)
                        ELSE 0
                    END AS prev_avg,

                    /* CURRENT FY AVG (ONLY FOR CURRENT FY ROW) */
                    CASE
                        WHEN b.fy_year = p.curr_fy_start
                        THEN
                            SUM(CASE WHEN s.fy_year = b.fy_year THEN s.amount ELSE 0 END)
                            / NULLIF(p.month_count, 0)
                        ELSE 0
                    END AS curr_avg,

                    /* TOTAL DIFFERENCE */
                    SUM(CASE WHEN s.fy_year = b.fy_year THEN s.amount ELSE 0 END)
                    -
                    SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END)
                    AS total_diff,

                    /* AVG DIFFERENCE */
                    CASE
                        WHEN b.fy_year = p.curr_fy_start
                        THEN
                            (
                                (
                                    SUM(CASE WHEN s.fy_year = b.fy_year THEN s.amount ELSE 0 END)
                                    -
                                    SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END)
                                ) / NULLIF(p.month_count, 0)
                            )
                        ELSE 0
                    END AS avg_diff,

                    /* % CHANGE */
                    CASE
                        WHEN b.fy_year = p.curr_fy_start
                             AND SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END) <> 0
                        THEN
                            (
                                (
                                    (
                                        SUM(CASE WHEN s.fy_year = b.fy_year THEN s.amount ELSE 0 END)
                                        -
                                        SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END)
                                    ) / NULLIF(p.month_count, 0)
                                )
                                /
                                (
                                    SUM(CASE WHEN s.fy_year = b.fy_year - 1 THEN s.amount ELSE 0 END)
                                    / NULLIF(p.month_count, 0)
                                )
                            ) * 100
                        ELSE 0
                    END AS pct_change

                FROM fy_base b
                LEFT JOIN sales s
                    ON s.territory_id = b.territory_id
                   AND s.doctor_id = b.doctor_id
                   AND s.doc_unique_id = b.doc_unique_id
                CROSS JOIN params p

                GROUP BY
                    b.territory_id,
                    b.doctor_id,
                    b.doc_unique_id,
                    b.fy_year,
                    p.curr_fy_start,
                    p.month_count
            )
        """)
