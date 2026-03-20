from odoo import models, fields, tools

class MrProductFyComparison(models.Model):
    _name = 'mr.product.fy.comparison'
    _description = 'Product Wise FY Sales (Previous FY vs Current FY)'
    _auto = False

    territory_id = fields.Many2one('territory.name', string="Territory", readonly=True)
    category_id = fields.Many2one('product.category', string="Division", readonly=True)
    product_id = fields.Many2one('product.product', string="Product", readonly=True)

    prev_qty = fields.Float(string="Prev FY Qty", readonly=True)
    prev_amt = fields.Float(string="Prev FY Amt", readonly=True)

    curr_qty = fields.Float(string="Curr FY Qty", readonly=True)
    curr_amt = fields.Float(string="Curr FY Amt", readonly=True)

    diff_qty = fields.Float(string="Diff Qty", readonly=True)
    diff_amt = fields.Float(string="Diff Amt", readonly=True)

    pct_qty = fields.Float(string="% Qty", readonly=True)
    pct_amt = fields.Float(string="% Amt", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mr_product_fy_comparison AS (

                WITH params AS (
                    SELECT
                        -- Current FY start (01-Apr of current FY)
                        CASE
                            WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                THEN make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, 4, 1)
                            ELSE make_date((EXTRACT(YEAR FROM CURRENT_DATE)::int - 1), 4, 1)
                        END AS curr_fy_start,

                        -- Current FY end (up to current month)
                        (date_trunc('month', CURRENT_DATE)
                            + INTERVAL '1 month - 1 day')::date AS curr_fy_end,

                        -- Previous FY start (01-Apr of previous FY)
                        CASE
                            WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                THEN make_date((EXTRACT(YEAR FROM CURRENT_DATE)::int - 1), 4, 1)
                            ELSE make_date((EXTRACT(YEAR FROM CURRENT_DATE)::int - 2), 4, 1)
                        END AS prev_fy_start,

                        -- Previous FY end (same month last year)
                        ((date_trunc('month', CURRENT_DATE)
                            + INTERVAL '1 month - 1 day')
                            - INTERVAL '1 year')::date AS prev_fy_end
                ),

                sales AS (
                    SELECT
                        doc.territory_id,
                        line.category_id,
                        line.product_id,
                        to_date(line.month, 'YYYY-MM') AS sale_date,
                        line.product_qty,
                        line.amount
                    FROM mr_doctor_line line
                    JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
                )

                SELECT
                    row_number() OVER () AS id,
                    s.territory_id,
                    s.category_id,
                    s.product_id,

                    -- Previous FY (up to current month)
                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                            THEN s.product_qty ELSE 0
                        END
                    ) AS prev_qty,

                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                            THEN s.amount ELSE 0
                        END
                    ) AS prev_amt,

                    -- Current FY (up to current month)
                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.curr_fy_start AND p.curr_fy_end
                            THEN s.product_qty ELSE 0
                        END
                    ) AS curr_qty,

                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.curr_fy_start AND p.curr_fy_end
                            THEN s.amount ELSE 0
                        END
                    ) AS curr_amt,

                    -- Difference (Current - Previous)
                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.curr_fy_start AND p.curr_fy_end
                            THEN s.product_qty ELSE 0
                        END
                    )
                    -
                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                            THEN s.product_qty ELSE 0
                        END
                    ) AS diff_qty,

                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.curr_fy_start AND p.curr_fy_end
                            THEN s.amount ELSE 0
                        END
                    )
                    -
                    SUM(
                        CASE
                            WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                            THEN s.amount ELSE 0
                        END
                    ) AS diff_amt,

                    -- % Qty Growth
                    CASE
                        WHEN SUM(
                            CASE
                                WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                                THEN s.product_qty ELSE 0
                            END
                        ) = 0
                        THEN 0
                        ELSE
                        (
                            (
                                SUM(
                                    CASE
                                        WHEN s.sale_date BETWEEN p.curr_fy_start AND p.curr_fy_end
                                        THEN s.product_qty ELSE 0
                                    END
                                )
                                -
                                SUM(
                                    CASE
                                        WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                                        THEN s.product_qty ELSE 0
                                    END
                                )
                            )
                            /
                            SUM(
                                CASE
                                    WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                                    THEN s.product_qty ELSE 0
                                END
                            )
                        ) * 100
                    END AS pct_qty,

                    -- % Amount Growth
                    CASE
                        WHEN SUM(
                            CASE
                                WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                                THEN s.amount ELSE 0
                            END
                        ) = 0
                        THEN 0
                        ELSE
                        (
                            (
                                SUM(
                                    CASE
                                        WHEN s.sale_date BETWEEN p.curr_fy_start AND p.curr_fy_end
                                        THEN s.amount ELSE 0
                                    END
                                )
                                -
                                SUM(
                                    CASE
                                        WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                                        THEN s.amount ELSE 0
                                    END
                                )
                            )
                            /
                            SUM(
                                CASE
                                    WHEN s.sale_date BETWEEN p.prev_fy_start AND p.prev_fy_end
                                    THEN s.amount ELSE 0
                                END
                            )
                        ) * 100
                    END AS pct_amt

                FROM sales s
                CROSS JOIN params p
                GROUP BY
                    s.territory_id,
                    s.category_id,
                    s.product_id
            )
        """)
