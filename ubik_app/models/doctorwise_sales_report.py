from odoo import models, fields, tools

class MrDoctorSalesReport(models.Model):
    _name = 'mr.doctor.sales.report'
    _description = 'Doctor Wise Sales Report'
    _auto = False
    
    ########### Code to show the top sales doctorwise in excel sheet when exporting data:starts ##################
    def read_group(
        self, domain, fields, groupby,
        offset=0, limit=None, orderby=False, lazy=True
    ):
        # Force total amount DESC for grouped results & exports
        if not orderby:
            orderby = 'amount:sum desc'

        return super().read_group(
            domain=domain,
            fields=fields,
            groupby=groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy
        )
    ########### Code to show the top sales doctorwise in excel sheet when exporting data:ends ##################
  
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
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
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
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW mr_doctor_sales_report AS (
            SELECT
                t.*,
                CASE
                    WHEN t.year = (
                        CASE
                            WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4 THEN
                                EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '-' ||
                                RIGHT((EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT, 2)
                            ELSE
                                (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '-' ||
                                RIGHT(EXTRACT(YEAR FROM CURRENT_DATE)::TEXT, 2)
                        END
                    )
                    THEN TRUE ELSE FALSE
                END AS is_current_fy
            FROM (
                SELECT
                    MIN(line.id) AS id,
                    doc.mr_id,
                    doc.doctor_id,
                    doc.territory_id,
                    rp.doc_unique_id,
                    line.category_id,
                    line.product_id,
                    line.rate_type,
                    line.price_unit,

                    (
                        CASE
                            WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                            THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                            ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) - 1
                        END
                    )::TEXT || '-' ||
                    RIGHT(
                        (
                            CASE
                                WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) + 1
                                ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                            END
                        )::TEXT, 2
                    ) AS year,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 4 THEN line.product_qty ELSE 0 END) AS apr_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 4 THEN line.amount ELSE 0 END) AS apr_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 5 THEN line.product_qty ELSE 0 END) AS may_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 5 THEN line.amount ELSE 0 END) AS may_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 6 THEN line.product_qty ELSE 0 END) AS jun_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 6 THEN line.amount ELSE 0 END) AS jun_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 7 THEN line.product_qty ELSE 0 END) AS jul_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 7 THEN line.amount ELSE 0 END) AS jul_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 8 THEN line.product_qty ELSE 0 END) AS aug_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 8 THEN line.amount ELSE 0 END) AS aug_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 9 THEN line.product_qty ELSE 0 END) AS sep_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 9 THEN line.amount ELSE 0 END) AS sep_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 10 THEN line.product_qty ELSE 0 END) AS oct_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 10 THEN line.amount ELSE 0 END) AS oct_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 11 THEN line.product_qty ELSE 0 END) AS nov_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 11 THEN line.amount ELSE 0 END) AS nov_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 12 THEN line.product_qty ELSE 0 END) AS dec_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 12 THEN line.amount ELSE 0 END) AS dec_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 1 THEN line.product_qty ELSE 0 END) AS jan_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 1 THEN line.amount ELSE 0 END) AS jan_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 2 THEN line.product_qty ELSE 0 END) AS feb_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 2 THEN line.amount ELSE 0 END) AS feb_amt,

                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 3 THEN line.product_qty ELSE 0 END) AS mar_qty,
                    SUM(CASE WHEN EXTRACT(MONTH FROM TO_DATE(line.month,'YYYY-MM')) = 3 THEN line.amount ELSE 0 END) AS mar_amt,

                    SUM(line.product_qty) AS product_qty,
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
                    line.product_id,
                    line.rate_type,
                    line.price_unit,
                    year
            ) t
        )
        """)