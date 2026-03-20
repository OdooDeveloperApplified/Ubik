from odoo import models, fields, tools

# Helper model to make Remarks row editable leaving all other columns uneditable
class MrDoctorFinalSalesRemarks(models.Model):
    _name = 'mr.doctor.final.sales.remarks'
    _description = 'Doctor Final Sales Remarks'
    _rec_name = 'doctor_id'
    _order = 'territory_id, doctor_id'

    territory_id = fields.Many2one('territory.name', required=True, index=True)
    doctor_id = fields.Many2one('res.partner', required=True, index=True)
    fy_year = fields.Integer(required=True, index=True)
    month = fields.Char(required=True, index=True)
    remarks = fields.Text()

class MrDoctorFinalSalesReport(models.Model):
    _name = 'mr.doctor.final.sales.report'
    _description = 'Doctor Final Sales Report (FY Avg + Monthly)'
    _auto = False

    territory_id = fields.Many2one('territory.name', string="Territory",readonly=True)
    doctor_id = fields.Many2one('res.partner', string="Doctor Name",readonly=True)
    fy_year = fields.Integer(string="Fiscal Year", readonly=True)
    is_current_fy = fields.Boolean()

    prev_avg = fields.Float(readonly=True)
    curr_avg = fields.Float(readonly=True)
    total_diff = fields.Float(readonly=True)
    curr_month_total = fields.Float(readonly=True)
    nov_vs_avg_diff = fields.Float(string="Difference(Current FY Total Vs Current FY Avg)", readonly=True)

    remarks = fields.Text(inverse="_inverse_remarks", compute="_compute_remarks",)

    # Helper function to make create remarks and make it editable
    def _inverse_remarks(self):
        Remarks = self.env['mr.doctor.final.sales.remarks']
        today = fields.Date.today()

        fy_year = today.year if today.month >= 4 else today.year - 1
        month = today.strftime('%Y-%m')

        for rec in self:
            remark = Remarks.search([
                ('territory_id', '=', rec.territory_id.id),
                ('doctor_id', '=', rec.doctor_id.id),
                ('fy_year', '=', fy_year),
                ('month', '=', month),
            ], limit=1)

            if remark:
                remark.remarks = rec.remarks
            else:
                Remarks.create({
                    'territory_id': rec.territory_id.id,
                    'doctor_id': rec.doctor_id.id,
                    'fy_year': fy_year,
                    'month': month,
                    'remarks': rec.remarks,
                })

    # Helper function to make remarks column editable
    def _compute_remarks(self):
        Remarks = self.env['mr.doctor.final.sales.remarks']
        today = fields.Date.today()

        fy_year = today.year if today.month >= 4 else today.year - 1
        month = today.strftime('%Y-%m')

        for rec in self:
            remark = Remarks.search([
                ('territory_id', '=', rec.territory_id.id),
                ('doctor_id', '=', rec.doctor_id.id),
                ('fy_year', '=', fy_year),
                ('month', '=', month),
            ], limit=1)

            rec.remarks = remark.remarks if remark else False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mr_doctor_final_sales_report AS (

                WITH sales AS (
                    SELECT
                        doc.territory_id,
                        doc.doctor_id,
                        to_date(line.month, 'YYYY-MM') AS sale_date,
                        line.amount,
                        CASE
                            WHEN EXTRACT(MONTH FROM to_date(line.month,'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM to_date(line.month,'YYYY-MM'))
                            ELSE EXTRACT(YEAR FROM to_date(line.month,'YYYY-MM')) - 1
                        END AS fy_year
                    FROM mr_doctor_line line
                    JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
                ),

                fy_stats AS (
                    SELECT
                        territory_id,
                        doctor_id,
                        fy_year,
                        COUNT(DISTINCT date_trunc('month', sale_date)) AS month_count,
                        SUM(amount) AS fy_total
                    FROM sales
                    GROUP BY territory_id, doctor_id, fy_year
                )

                SELECT
                    row_number() OVER () AS id,
                    s.territory_id,
                    s.doctor_id,
                    s.fy_year,
                            
                    CASE
                        WHEN s.fy_year = (
                            CASE
                                WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                    THEN EXTRACT(YEAR FROM CURRENT_DATE)
                                ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                            END
                        )
                        THEN TRUE
                        ELSE FALSE
                    END AS is_current_fy,

                    -- Previous FY average
                    (
                        SELECT fs_prev.fy_total / NULLIF(fs_prev.month_count, 0)
                        FROM fy_stats fs_prev
                        WHERE fs_prev.territory_id = s.territory_id
                          AND fs_prev.doctor_id = s.doctor_id
                          AND fs_prev.fy_year = s.fy_year - 1
                    ) AS prev_avg,

                    -- Current FY average
                    fs.fy_total / NULLIF(fs.month_count, 0) AS curr_avg,

                    -- FY total difference (Curr - Prev)
                    fs.fy_total
                    -
                    COALESCE((
                        SELECT fs_prev.fy_total
                        FROM fy_stats fs_prev
                        WHERE fs_prev.territory_id = s.territory_id
                          AND fs_prev.doctor_id = s.doctor_id
                          AND fs_prev.fy_year = s.fy_year - 1
                    ), 0) AS total_diff,

                    -- Current calendar month total (only affects current FY rows)
                    SUM(
                        CASE
                            WHEN date_trunc('month', s.sale_date) =
                                 date_trunc('month', CURRENT_DATE)
                            THEN s.amount ELSE 0
                        END
                    ) AS curr_month_total,

                    -- FY total - FY average
                    fs.fy_total - (fs.fy_total / NULLIF(fs.month_count, 0))
                    AS nov_vs_avg_diff,

                    MAX(r.remarks) AS remarks

                FROM sales s
                JOIN fy_stats fs
                  ON fs.territory_id = s.territory_id
                 AND fs.doctor_id = s.doctor_id
                 AND fs.fy_year = s.fy_year

                LEFT JOIN mr_doctor_final_sales_remarks r
                  ON r.territory_id = s.territory_id
                 AND r.doctor_id = s.doctor_id
                 AND r.fy_year = s.fy_year

                GROUP BY
                    s.territory_id,
                    s.doctor_id,
                    s.fy_year,
                    is_current_fy,
                    fs.fy_total,
                    fs.month_count
            )
        """)


