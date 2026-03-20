from odoo import models, fields, tools

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
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW doctor_division_sales_report AS (
                SELECT
                    MIN(line.id) AS id,
                    doc.mr_id AS mr_id,
                    doc.doctor_id AS doctor_id,
                    doc.territory_id AS territory_id,
                    rp.doc_unique_id AS doc_unique_id,
                    line.category_id AS category_id,

                    (
                        CASE
                            WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                            ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) - 1
                        END
                    )::text
                    || '-' ||
                    RIGHT(
                        (
                            CASE
                                WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) + 1
                                ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                            END
                        )::text, 2
                    ) AS year,
                            
                    -- Current FY Flag
                    (
                        (
                            CASE
                                WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                    THEN EXTRACT(YEAR FROM CURRENT_DATE)
                                ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                            END
                        )::text
                        || '-' ||
                        RIGHT(
                            (
                                CASE
                                    WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                        THEN EXTRACT(YEAR FROM CURRENT_DATE) + 1
                                    ELSE EXTRACT(YEAR FROM CURRENT_DATE)
                                END
                            )::text,
                            2
                        )
                    )
                    =
                    (
                        CASE
                            WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                            ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) - 1
                        END
                    )::text
                    || '-' ||
                    RIGHT(
                        (
                            CASE
                                WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                                    THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) + 1
                                ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                            END
                        )::text,
                        2
                    ) AS is_current_fy,

                    -- Monthly category totals
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 4 THEN line.amount ELSE 0 END) AS apr_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 5 THEN line.amount ELSE 0 END) AS may_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 6 THEN line.amount ELSE 0 END) AS jun_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 7 THEN line.amount ELSE 0 END) AS jul_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 8 THEN line.amount ELSE 0 END) AS aug_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 9 THEN line.amount ELSE 0 END) AS sep_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 10 THEN line.amount ELSE 0 END) AS oct_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 11 THEN line.amount ELSE 0 END) AS nov_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 12 THEN line.amount ELSE 0 END) AS dec_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 1 THEN line.amount ELSE 0 END) AS jan_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 2 THEN line.amount ELSE 0 END) AS feb_amt,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) = 3 THEN line.amount ELSE 0 END) AS mar_amt,

                    SUM(line.amount) AS amount

                FROM mr_doctor_line line
                JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
                JOIN res_partner rp ON rp.id = doc.doctor_id

                GROUP BY
                    doc.mr_id,
                    doc.doctor_id,
                    doc.territory_id,
                    rp.doc_unique_id,
                    line.category_id,
                    year
            )
        """)
