from odoo import models, fields, tools, api
from datetime import date

# ------------------------------------------------------------------
# Territory Monthly Target (UNCHANGED – REQUIRED)
# ------------------------------------------------------------------
class MrTerritoryTarget(models.Model):
    _name = 'mr.territory.target'
    _description = 'Territory Monthly Target'

    territory_id = fields.Many2one('territory.name', required=True)
    fiscal_year = fields.Char(required=True)  # e.g. 2025-26
    month = fields.Selection([
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
    ], required=True)

    target_amount = fields.Float(required=True)

class MrTargetAchievementYearlyTarget(models.Model):
    _name = 'mr.target.achievement.yearly.target'
    _description = 'MR Yearly Target (Editable)'
    _rec_name = 'mr_id'
    _order = 'territory_id, mr_id, category_id, fiscal_year'

    territory_id = fields.Many2one('territory.name', required=True, index=True)
    mr_id = fields.Many2one('res.users', required=True, index=True)
    category_id = fields.Many2one('product.category', required=True, index=True)
    fiscal_year = fields.Char(required=True, index=True)   # e.g. 2025-26
    yearly_target = fields.Float(string="Yearly Target")

class MrQuarterlyTarget(models.Model):
    _name = 'mr.quarterly.target'
    _description = 'MR Quarterly Target'

    territory_id = fields.Many2one('territory.name', required=True)
    mr_id = fields.Many2one('res.users', required=True)
    category_id = fields.Many2one('product.category', required=True)
    fiscal_year = fields.Char(required=True)
    quarter = fields.Selection([
        ('q1', 'Q1'),
        ('q2', 'Q2'),
        ('q3', 'Q3'),
        ('q4', 'Q4'),
    ], required=True)
    target_amount = fields.Float(required=True)

# ------------------------------------------------------------------
# Quarterly Target vs Achievement Report (VIEW)
# ------------------------------------------------------------------
class MrTargetAchievementQuarterlyReport(models.Model):
    _name = 'mr.target.achievement.quarterly.report'
    _description = 'Target vs Achievement Quarterly Report'
    _auto = False

    territory_id = fields.Many2one('territory.name', readonly=True)
    mr_id = fields.Many2one('res.users', string="MR Name", readonly=True)
    fiscal_year = fields.Char(string="Fiscal Year", readonly=True)
    is_current_fy = fields.Boolean()
    category_id = fields.Many2one('product.category', string="Division", readonly=True)

    # ================= YEARLY TARGET (EDITABLE) =================
    yearly_target = fields.Float(string="Yearly Target",compute="_compute_yearly_target",inverse="_inverse_yearly_target",readonly=False)

    def _compute_yearly_target(self):
        Target = self.env['mr.target.achievement.yearly.target']

        for rec in self:
            target = Target.search([
                ('territory_id', '=', rec.territory_id.id),
                ('mr_id', '=', rec.mr_id.id),
                ('category_id', '=', rec.category_id.id),
                ('fiscal_year', '=', rec.fiscal_year),
            ], limit=1)

            rec.yearly_target = target.yearly_target if target else 0.0

    # Old code for inverse method without audit logging starts here
    # def _inverse_yearly_target(self):
    #     Target = self.env['mr.target.achievement.yearly.target']

    #     for rec in self:
    #         target = Target.search([
    #             ('territory_id', '=', rec.territory_id.id),
    #             ('mr_id', '=', rec.mr_id.id),
    #             ('category_id', '=', rec.category_id.id),
    #             ('fiscal_year', '=', rec.fiscal_year),
    #         ], limit=1)

    #         if target:
    #             target.yearly_target = rec.yearly_target
    #         else:
    #             Target.create({
    #                 'territory_id': rec.territory_id.id,
    #                 'mr_id': rec.mr_id.id,
    #                 'category_id': rec.category_id.id,
    #                 'fiscal_year': rec.fiscal_year,
    #                 'yearly_target': rec.yearly_target,
    #             })
    # Old code for inverse method without audit logging ends here

    # New code to add audit log for changes in yearly target starts here
    def _inverse_yearly_target(self):
        for rec in self:
            target = self.env['mr.target.achievement.yearly.target'].search([
                ('territory_id', '=', rec.territory_id.id),
                ('mr_id', '=', rec.mr_id.id),
                ('category_id', '=', rec.category_id.id),
                ('fiscal_year', '=', rec.fiscal_year),
            ], limit=1)

            old = target.yearly_target if target else 0.0

            if not target:
                target = self.env['mr.target.achievement.yearly.target'].create({
                    'territory_id': rec.territory_id.id,
                    'mr_id': rec.mr_id.id,
                    'category_id': rec.category_id.id,
                    'fiscal_year': rec.fiscal_year,
                    'yearly_target': rec.yearly_target,
                })
            else:
                target.yearly_target = rec.yearly_target

            # 🔹 AUDIT LOG
            if old != rec.yearly_target:
                self.env['mr.target.audit.log'].create({
                    'user_id': self.env.user.id,
                    'territory_id': rec.territory_id.id,
                    'mr_id': rec.mr_id.id,
                    'category_id': rec.category_id.id,
                    'fiscal_year': rec.fiscal_year,
                    'field_name': 'Yearly Target',
                    'old_value': old,
                    'new_value': rec.yearly_target,
                })
    # New code to add audit log for changes in yearly target ends here
    
    # ================= MONTHLY TARGETS (EDITABLE) =================
    def _get_month_target(self, month):
        return self.env['mr.territory.target'].search([
            ('territory_id', '=', self.territory_id.id),
            ('fiscal_year', '=', self.fiscal_year),
            ('month', '=', month),
        ], limit=1)
    

    #### Old code for setting month target without audit log starts here
    # def _set_month_target(self, month, value):
    #     Target = self.env['mr.territory.target']
    #     t = self._get_month_target(month)
    #     if t:
    #         t.target_amount = value
    #     else:
    #         Target.create({
    #             'territory_id': self.territory_id.id,
    #             'fiscal_year': self.fiscal_year,
    #             'month': month,
    #             'target_amount': value,
    #         })
    #### Old code for setting month target without audit log ends here

    # New code to set month target with audit log starts here
    def _set_month_target(self, month, value):
        Target = self.env['mr.territory.target']
        t = self._get_month_target(month)

        old_value = t.target_amount if t else 0.0

        if t:
            t.target_amount = value
        else:
            Target.create({
                'territory_id': self.territory_id.id,
                'fiscal_year': self.fiscal_year,
                'month': month,
                'target_amount': value,
            })

        # 🔹 MONTHLY AUDIT LOG (ONLY WHEN VALUE CHANGES)
        if old_value != value:
            self.env['mr.target.audit.log'].create({
                'user_id': self.env.user.id,
                'territory_id': self.territory_id.id,
                'mr_id': self.mr_id.id,
                'category_id': self.category_id.id,
                'fiscal_year': self.fiscal_year,
                'field_name': f'Monthly Target ({month})',
                'old_value': old_value,
                'new_value': value,
            })
    # New code to set month target with audit log ends here

    def _make_month_fields(month):
        def compute(self):
            for rec in self:
                t = rec._get_month_target(month)
                setattr(rec, f'{month}_tgt', t.target_amount if t else 0.0)

        def inverse(self):
            for rec in self:
                rec._set_month_target(month, getattr(rec, f'{month}_tgt'))

        return compute, inverse
    
    MONTH_LABELS = {
    '04': 'Apr Tgt',
    '05': 'May Tgt',
    '06': 'Jun Tgt',
    '07': 'Jul Tgt',
    '08': 'Aug Tgt',
    '09': 'Sep Tgt',
    '10': 'Oct Tgt',
    '11': 'Nov Tgt',
    '12': 'Dec Tgt',
    '01': 'Jan Tgt',
    '02': 'Feb Tgt',
    '03': 'Mar Tgt',}


    for m, label in MONTH_LABELS.items():
        c, i = _make_month_fields(m)
        locals()[f'{m}_tgt'] = fields.Float(string=label, compute=c, inverse=i, readonly=False)
    
    # ---------------- Q1 ----------------
    # apr_tgt = fields.Float(readonly=True)
    apr_ach = fields.Float(readonly=True)
    apr_sur_def = fields.Float(readonly=True)
    apr_pct = fields.Float(readonly=True)

    # may_tgt = fields.Float(readonly=True)
    may_ach = fields.Float(readonly=True)
    may_sur_def = fields.Float(readonly=True)
    may_pct = fields.Float(readonly=True)

    # jun_tgt = fields.Float(readonly=True)
    jun_ach = fields.Float(readonly=True)
    jun_sur_def = fields.Float(readonly=True)
    jun_pct = fields.Float(readonly=True)

    # ---------------- Q2 ----------------
    # jul_tgt = fields.Float(readonly=True)
    jul_ach = fields.Float(readonly=True)
    jul_sur_def = fields.Float(readonly=True)
    jul_pct = fields.Float(readonly=True)

    # aug_tgt = fields.Float(readonly=True)
    aug_ach = fields.Float(readonly=True)
    aug_sur_def = fields.Float(readonly=True)
    aug_pct = fields.Float(readonly=True)

    # sep_tgt = fields.Float(readonly=True)
    sep_ach = fields.Float(readonly=True)
    sep_sur_def = fields.Float(readonly=True)
    sep_pct = fields.Float(readonly=True)

    # ---------------- Q3 ----------------
    # oct_tgt = fields.Float(readonly=True)
    oct_ach = fields.Float(readonly=True)
    oct_sur_def = fields.Float(readonly=True)
    oct_pct = fields.Float(readonly=True)

    # nov_tgt = fields.Float(readonly=True)
    nov_ach = fields.Float(readonly=True)
    nov_sur_def = fields.Float(readonly=True)
    nov_pct = fields.Float(readonly=True)

    # dec_tgt = fields.Float(readonly=True)
    dec_ach = fields.Float(readonly=True)
    dec_sur_def = fields.Float(readonly=True)
    dec_pct = fields.Float(readonly=True)

    # ---------------- Q4 ----------------
    # jan_tgt = fields.Float(readonly=True)
    jan_ach = fields.Float(readonly=True)
    jan_sur_def = fields.Float(readonly=True)
    jan_pct = fields.Float(readonly=True)

    # feb_tgt = fields.Float(readonly=True)
    feb_ach = fields.Float(readonly=True)
    feb_sur_def = fields.Float(readonly=True)
    feb_pct = fields.Float(readonly=True)

    # mar_tgt = fields.Float(readonly=True)
    mar_ach = fields.Float(readonly=True)
    mar_sur_def = fields.Float(readonly=True)
    mar_pct = fields.Float(readonly=True)

    # ---------------- Quarterly Totals ----------------
    q1_tgt = fields.Float(readonly=True)
    q1_ach = fields.Float(readonly=True)
    q1_sur_def = fields.Float(readonly=True)
    q1_pct = fields.Float(readonly=True)

    q2_tgt = fields.Float(readonly=True)
    q2_ach = fields.Float(readonly=True)
    q2_sur_def = fields.Float(readonly=True)
    q2_pct = fields.Float(readonly=True)

    q3_tgt = fields.Float(readonly=True)
    q3_ach = fields.Float(readonly=True)
    q3_sur_def = fields.Float(readonly=True)
    q3_pct = fields.Float(readonly=True)

    q4_tgt = fields.Float(readonly=True)
    q4_ach = fields.Float(readonly=True)
    q4_sur_def = fields.Float(readonly=True)
    q4_pct = fields.Float(readonly=True)

    # Full Year
    fy_tgt = fields.Float(readonly=True)
    fy_ach = fields.Float(readonly=True)
    fy_sur_def = fields.Float(readonly=True)
    fy_pct = fields.Float(readonly=True)

    # New code to add button action for viewing change history
    def action_view_change_history(self):
        self.ensure_one()
        return {
            'name': 'Change History',
            'type': 'ir.actions.act_window',
            'res_model': 'mr.target.audit.log',
            'view_mode': 'list',
            'views': [(self.env.ref('ubik_app.view_mr_target_audit_log_tree').id, 'list')],
            'domain': [
                ('territory_id', '=', self.territory_id.id),
                ('mr_id', '=', self.mr_id.id),
                ('category_id', '=', self.category_id.id),
                ('fiscal_year', '=', self.fiscal_year),
            ],
            'context': {'create': False},
        }
    # New code for button action to show change history ends here

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE VIEW mr_target_achievement_quarterly_report AS (
                SELECT
                    row_number() OVER () AS id,
                    fy.territory_id,
                    fy.mr_id,
                    fy.category_id,
                    fy.fiscal_year,
                    CASE
                        WHEN fy.fiscal_year = (
                            CASE
                                WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                                THEN EXTRACT(YEAR FROM CURRENT_DATE)::text || '-' ||
                                    RIGHT((EXTRACT(YEAR FROM CURRENT_DATE)+1)::text, 2)
                                ELSE (EXTRACT(YEAR FROM CURRENT_DATE)-1)::text || '-' ||
                                    RIGHT(EXTRACT(YEAR FROM CURRENT_DATE)::text, 2)
                            END
                        )
                        THEN TRUE
                        ELSE FALSE
                    END AS is_current_fy,

                    /* APR */
                    SUM(CASE WHEN fy.mm='04' THEN t.target_amount ELSE 0 END) AS apr_tgt,
                    SUM(CASE WHEN fy.mm='04' THEN fy.amt ELSE 0 END) AS apr_ach,
                    SUM(CASE WHEN fy.mm='04' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='04' THEN t.target_amount ELSE 0 END) AS apr_sur_def,
                    ROUND(
                            (
                            SUM(CASE WHEN fy.mm='04' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='04' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS apr_pct,

                    /* MAY */
                    SUM(CASE WHEN fy.mm='05' THEN t.target_amount ELSE 0 END) AS may_tgt,
                    SUM(CASE WHEN fy.mm='05' THEN fy.amt ELSE 0 END) AS may_ach,
                    SUM(CASE WHEN fy.mm='05' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='05' THEN t.target_amount ELSE 0 END) AS may_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='05' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='05' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS may_pct,

                    /* JUN */
                    SUM(CASE WHEN fy.mm='06' THEN t.target_amount ELSE 0 END) AS jun_tgt,
                    SUM(CASE WHEN fy.mm='06' THEN fy.amt ELSE 0 END) AS jun_ach,
                    SUM(CASE WHEN fy.mm='06' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='06' THEN t.target_amount ELSE 0 END) AS jun_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='06' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='06' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS jun_pct,

                    /* JUL */
                    SUM(CASE WHEN fy.mm='07' THEN t.target_amount ELSE 0 END) AS jul_tgt,
                    SUM(CASE WHEN fy.mm='07' THEN fy.amt ELSE 0 END) AS jul_ach,
                    SUM(CASE WHEN fy.mm='07' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='07' THEN t.target_amount ELSE 0 END) AS jul_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='07' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='07' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS jul_pct,

                    /* AUG */
                    SUM(CASE WHEN fy.mm='08' THEN t.target_amount ELSE 0 END) AS aug_tgt,
                    SUM(CASE WHEN fy.mm='08' THEN fy.amt ELSE 0 END) AS aug_ach,
                    SUM(CASE WHEN fy.mm='08' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='08' THEN t.target_amount ELSE 0 END) AS aug_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='08' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='08' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS aug_pct,

                    /* SEP */
                    SUM(CASE WHEN fy.mm='09' THEN t.target_amount ELSE 0 END) AS sep_tgt,
                    SUM(CASE WHEN fy.mm='09' THEN fy.amt ELSE 0 END) AS sep_ach,
                    SUM(CASE WHEN fy.mm='09' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='09' THEN t.target_amount ELSE 0 END) AS sep_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='09' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='09' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS sep_pct,
                            
                    /* OCT */
                    SUM(CASE WHEN fy.mm='10' THEN t.target_amount ELSE 0 END) AS oct_tgt,
                    SUM(CASE WHEN fy.mm='10' THEN fy.amt ELSE 0 END) AS oct_ach,
                    SUM(CASE WHEN fy.mm='10' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='10' THEN t.target_amount ELSE 0 END) AS oct_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='10' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='10' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS oct_pct,
                    
                    /* NOV */
                    SUM(CASE WHEN fy.mm='11' THEN t.target_amount ELSE 0 END) AS nov_tgt,
                    SUM(CASE WHEN fy.mm='11' THEN fy.amt ELSE 0 END) AS nov_ach,
                    SUM(CASE WHEN fy.mm='11' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='11' THEN t.target_amount ELSE 0 END) AS nov_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='11' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='11' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS nov_pct,
                    
                    /* DEC */
                    SUM(CASE WHEN fy.mm='12' THEN t.target_amount ELSE 0 END) AS dec_tgt,
                    SUM(CASE WHEN fy.mm='12' THEN fy.amt ELSE 0 END) AS dec_ach,
                    SUM(CASE WHEN fy.mm='12' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='12' THEN t.target_amount ELSE 0 END) AS dec_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='12' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='12' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS dec_pct,
                            
                    /* JAN */
                    SUM(CASE WHEN fy.mm='01' THEN t.target_amount ELSE 0 END) AS jan_tgt,
                    SUM(CASE WHEN fy.mm='01' THEN fy.amt ELSE 0 END) AS jan_ach,
                    SUM(CASE WHEN fy.mm='01' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='01' THEN t.target_amount ELSE 0 END) AS jan_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='01' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='01' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS jan_pct,
                    
                    /* FEB */
                    SUM(CASE WHEN fy.mm='02' THEN t.target_amount ELSE 0 END) AS feb_tgt,
                    SUM(CASE WHEN fy.mm='02' THEN fy.amt ELSE 0 END) AS feb_ach,
                    SUM(CASE WHEN fy.mm='02' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='02' THEN t.target_amount ELSE 0 END) AS feb_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='02' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='02' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS feb_pct,
                            
                    /* MAR */
                    SUM(CASE WHEN fy.mm='03' THEN t.target_amount ELSE 0 END) AS mar_tgt,
                    SUM(CASE WHEN fy.mm='03' THEN fy.amt ELSE 0 END) AS mar_ach,
                    SUM(CASE WHEN fy.mm='03' THEN fy.amt ELSE 0 END)
                      - SUM(CASE WHEN fy.mm='03' THEN t.target_amount ELSE 0 END) AS mar_sur_def,
                    ROUND((SUM(CASE WHEN fy.mm='03' THEN fy.amt ELSE 0 END)
                          / NULLIF(SUM(CASE WHEN fy.mm='03' THEN t.target_amount ELSE 0 END),0) 
                          * 100
                        )::numeric, 2
                    ) AS mar_pct,
                            
                    /* ================= Q1 (APR–JUN) ================= */
                    SUM(CASE WHEN fy.mm IN ('04','05','06') THEN t.target_amount ELSE 0 END) AS q1_tgt,
                    SUM(CASE WHEN fy.mm IN ('04','05','06') THEN fy.amt ELSE 0 END) AS q1_ach,
                    SUM(CASE WHEN fy.mm IN ('04','05','06') THEN fy.amt ELSE 0 END)
                    - SUM(CASE WHEN fy.mm IN ('04','05','06') THEN t.target_amount ELSE 0 END) AS q1_sur_def,
                    ROUND(
                        (
                            SUM(CASE WHEN fy.mm IN ('04','05','06') THEN fy.amt ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN fy.mm IN ('04','05','06') THEN t.target_amount ELSE 0 END), 0)
                            * 100
                        )::numeric, 2
                    ) AS q1_pct,

                    /* ================= Q2 (JUL–SEP) ================= */
                    SUM(CASE WHEN fy.mm IN ('07','08','09') THEN t.target_amount ELSE 0 END) AS q2_tgt,
                    SUM(CASE WHEN fy.mm IN ('07','08','09') THEN fy.amt ELSE 0 END) AS q2_ach,
                    SUM(CASE WHEN fy.mm IN ('07','08','09') THEN fy.amt ELSE 0 END)
                    - SUM(CASE WHEN fy.mm IN ('07','08','09') THEN t.target_amount ELSE 0 END) AS q2_sur_def,
                    ROUND(
                        (
                            SUM(CASE WHEN fy.mm IN ('07','08','09') THEN fy.amt ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN fy.mm IN ('07','08','09') THEN t.target_amount ELSE 0 END), 0)
                            * 100
                        )::numeric, 2
                    ) AS q2_pct,

                    /* ================= Q3 (OCT–DEC) ================= */
                    SUM(CASE WHEN fy.mm IN ('10','11','12') THEN t.target_amount ELSE 0 END) AS q3_tgt,
                    SUM(CASE WHEN fy.mm IN ('10','11','12') THEN fy.amt ELSE 0 END) AS q3_ach,
                    SUM(CASE WHEN fy.mm IN ('10','11','12') THEN fy.amt ELSE 0 END)
                    - SUM(CASE WHEN fy.mm IN ('10','11','12') THEN t.target_amount ELSE 0 END) AS q3_sur_def,
                    ROUND(
                        (
                            SUM(CASE WHEN fy.mm IN ('10','11','12') THEN fy.amt ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN fy.mm IN ('10','11','12') THEN t.target_amount ELSE 0 END), 0)
                            * 100
                        )::numeric, 2
                    ) AS q3_pct,

                    /* ================= Q4 (JAN–MAR) ================= */
                    SUM(CASE WHEN fy.mm IN ('01','02','03') THEN t.target_amount ELSE 0 END) AS q4_tgt,
                    SUM(CASE WHEN fy.mm IN ('01','02','03') THEN fy.amt ELSE 0 END) AS q4_ach,
                    SUM(CASE WHEN fy.mm IN ('01','02','03') THEN fy.amt ELSE 0 END)
                    - SUM(CASE WHEN fy.mm IN ('01','02','03') THEN t.target_amount ELSE 0 END) AS q4_sur_def,
                    ROUND(
                        (
                            SUM(CASE WHEN fy.mm IN ('01','02','03') THEN fy.amt ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN fy.mm IN ('01','02','03') THEN t.target_amount ELSE 0 END), 0)
                            * 100
                        )::numeric, 2
                    ) AS q4_pct,

                            
                    /* FY */
                    SUM(t.target_amount) AS fy_tgt,
                    SUM(fy.amt) AS fy_ach,
                    SUM(fy.amt) - SUM(t.target_amount) AS fy_sur_def,
                    ROUND(
                        (
                            SUM(fy.amt)
                            / NULLIF(SUM(t.target_amount), 0)
                            * 100
                        )::numeric, 2
                    ) AS fy_pct

                FROM (
                    SELECT
                        l.amount AS amt,
                        l.category_id,
                        d.territory_id,
                        SUBSTRING(l.month, 6, 2) AS mm,
                        (
                            CASE
                                WHEN EXTRACT(MONTH FROM TO_DATE(l.month,'YYYY-MM')) >= 4
                                THEN EXTRACT(YEAR FROM TO_DATE(l.month,'YYYY-MM'))
                                ELSE EXTRACT(YEAR FROM TO_DATE(l.month,'YYYY-MM')) - 1
                            END
                        )::text || '-' ||
                        RIGHT(
                            (
                                CASE
                                    WHEN EXTRACT(MONTH FROM TO_DATE(l.month,'YYYY-MM')) >= 4
                                    THEN EXTRACT(YEAR FROM TO_DATE(l.month,'YYYY-MM')) + 1
                                    ELSE EXTRACT(YEAR FROM TO_DATE(l.month,'YYYY-MM'))
                                END
                            )::text, 2
                        ) AS fiscal_year,
                        d.mr_id
                    FROM mr_doctor_line l
                    JOIN mr_doctor d ON d.id = l.mr_doctor_id
                ) fy
               LEFT JOIN mr_territory_target t
                    ON t.territory_id = fy.territory_id
                    AND t.month = fy.mm
                    AND t.fiscal_year = fy.fiscal_year

                GROUP BY
                    fy.territory_id,
                    fy.mr_id,
                    fy.category_id,
                    fy.fiscal_year
            )
        """)

# New code to add tracking functionality for changes in targets
class MrTargetAuditLog(models.Model):
    _name = 'mr.target.audit.log'
    _description = 'Target Change History'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string="Changed By", readonly=True)
    change_date = fields.Datetime(string="Changed On", default=fields.Datetime.now, readonly=True)
    territory_id = fields.Many2one('territory.name', readonly=True)
    mr_id = fields.Many2one('res.users', string="MR", readonly=True)
    category_id = fields.Many2one('product.category', readonly=True)
    fiscal_year = fields.Char(readonly=True)
    field_name = fields.Char(string="Field", readonly=True)
    old_value = fields.Float(readonly=True)
    new_value = fields.Float(readonly=True)