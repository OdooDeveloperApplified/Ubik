from odoo import models, fields, tools
import logging

_logger = logging.getLogger(__name__)

class MrDoctorAvgSalesReport(models.Model):
    _name = 'mr.doctor.avg.sales.report'
    _description = 'Doctor Avg Sales Comparison (FY)'
    _auto = False
    _rec_name = 'doctor_id'

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
        _logger.info("CREATING VIEW mr_doctor_avg_sales_report")
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Optimized query using CTE approach
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW mr_doctor_avg_sales_report AS (
            WITH 
            -- Get current fiscal year and month count
            params AS (
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
            
            -- Base sales data with safe numeric conversion
            sales_base AS (
                SELECT
                    doc.territory_id,
                    doc.doctor_id,
                    rp.doc_unique_id,
                    COALESCE(NULLIF(line.amount::text, 'NaN')::numeric, 0) AS amount,
                    
                    CASE
                        WHEN EXTRACT(MONTH FROM TO_DATE(line.month, 'YYYY-MM')) >= 4
                            THEN EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM'))
                        ELSE EXTRACT(YEAR FROM TO_DATE(line.month, 'YYYY-MM')) - 1
                    END AS fy_year
                    
                FROM mr_doctor_line line
                INNER JOIN mr_doctor doc ON doc.id = line.mr_doctor_id
                INNER JOIN res_partner rp ON rp.id = doc.doctor_id
                WHERE line.amount IS NOT NULL AND line.amount != 0
            ),
            
            -- Aggregate sales by doctor and fiscal year
            sales_aggregated AS (
                SELECT
                    territory_id,
                    doctor_id,
                    doc_unique_id,
                    fy_year,
                    SUM(amount) AS total_amount
                FROM sales_base
                GROUP BY territory_id, doctor_id, doc_unique_id, fy_year
            ),
            
            -- Get current fiscal year data with previous year
            fy_data AS (
                SELECT
                    s_curr.territory_id,
                    s_curr.doctor_id,
                    s_curr.doc_unique_id,
                    s_curr.fy_year,
                    COALESCE(s_curr.total_amount, 0) AS curr_total,
                    COALESCE(s_prev.total_amount, 0) AS prev_total
                FROM sales_aggregated s_curr
                LEFT JOIN sales_aggregated s_prev 
                    ON s_prev.territory_id = s_curr.territory_id
                    AND s_prev.doctor_id = s_curr.doctor_id
                    AND s_prev.doc_unique_id = s_curr.doc_unique_id
                    AND s_prev.fy_year = s_curr.fy_year - 1
                WHERE s_curr.fy_year >= (SELECT curr_fy_start - 1 FROM params)
            )
            
            -- Final selection with calculations
            SELECT
                ROW_NUMBER() OVER () AS id,
                fd.territory_id,
                fd.doctor_id,
                fd.doc_unique_id,
                fd.fy_year || '-' || RIGHT((fd.fy_year + 1)::text, 2) AS fiscal_year,
                
                -- Current FY flag
                (fd.fy_year = p.curr_fy_start) AS is_current_fy,
                
                -- Totals
                fd.prev_total AS prev_total,
                fd.curr_total AS curr_total,
                
                -- Averages (only for current FY)
                CASE 
                    WHEN fd.fy_year = p.curr_fy_start AND p.month_count > 0 
                    THEN fd.prev_total / p.month_count 
                    ELSE 0 
                END AS prev_avg,
                
                CASE 
                    WHEN fd.fy_year = p.curr_fy_start AND p.month_count > 0 
                    THEN fd.curr_total / p.month_count 
                    ELSE 0 
                END AS curr_avg,
                
                -- Differences
                (fd.curr_total - fd.prev_total) AS total_diff,
                
                CASE 
                    WHEN fd.fy_year = p.curr_fy_start AND p.month_count > 0 
                    THEN (fd.curr_total - fd.prev_total) / p.month_count 
                    ELSE 0 
                END AS avg_diff,
                
                -- Percentage change
                CASE 
                    WHEN fd.fy_year = p.curr_fy_start 
                        AND p.month_count > 0 
                        AND fd.prev_total != 0 
                    THEN ((fd.curr_total - fd.prev_total) / NULLIF(fd.prev_total, 0)) * 100
                    ELSE 0 
                END AS pct_change
                
            FROM fy_data fd
            CROSS JOIN params p
        )
        """)