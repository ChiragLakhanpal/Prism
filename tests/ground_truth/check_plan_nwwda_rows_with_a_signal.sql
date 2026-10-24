-- How many activities in the Northern Water Works Development Agency's Procurement Plan of October 9,
-- 2026 for P156634 carry a signal (needs a look or watch) as of October 22, 2026: the rows "Draft
-- review notes (3 rows)" drafts a note on (ticket 35), which check_plan's counts.signal gives.
-- Each check is plain SQL over the plan reader's tables, apart from check_plan's own code, as in
-- check_plan_nwwda_2026_10_09.sql. An activity counts once, whatever else it carries.
--
-- The expected count is the blueprint's Check a plan wireframe's: one activity needs a look and two
-- are worth watching (tests/ground_truth/values.toml, each plan_row's wireframe_mark).
--
-- The thresholds are config/thresholds.toml's [plan_check] values. Changing one there means
-- changing it here in the same change (CLAUDE.md rule 4).
-- param: agency = Northern Water Works Development Agency
-- param: plan_date = 2026-10-09
-- param: as_of = 2026-10-22
-- param: completion_passed_min_estimated_usd = 1000000
-- param: days_before_closing = 90
-- param: actual_to_estimate_ratio = 2.0
-- expect: activities_with_a_signal
-- expect: 3
WITH activity AS (
  SELECT
    r.estimated_amount_usd AS estimated,
    r.actual_amount_usd AS actual,
    sc.actual_on IS NOT NULL OR r.process_status IN ('Signed', 'Completed') AS signed,
    sc.actual_on IS NULL
      AND COALESCE(r.process_status, 'Pending Implementation')
        IN ('Pending Implementation', 'Under Implementation', 'Under Review', 'Draft') AS pending,
    COALESCE(cc.first_planned_on, cc.planned_on) AS planned_completion,
    datediff(p.closing_date, CAST(:as_of AS DATE)) AS days_to_close
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  JOIN strata.gold.project AS p ON p.project_id = v.project_id
  LEFT JOIN strata.silver.plan_step_delays AS sc
    ON sc.document_id = r.document_id
    AND sc.activity_reference_no = r.activity_reference_no
    AND sc.step = 'Signed Contract'
  LEFT JOIN strata.silver.plan_step_delays AS cc
    ON cc.document_id = r.document_id
    AND cc.activity_reference_no = r.activity_reference_no
    AND cc.step = 'Contract Completion'
  WHERE v.implementing_agency = :agency
    AND v.plan_date = CAST(:plan_date AS DATE)
)
SELECT count(*) AS activities_with_a_signal
FROM activity
WHERE (pending
    AND (estimated IS NULL OR estimated >= CAST(:completion_passed_min_estimated_usd AS DECIMAL(18, 2)))
    AND planned_completion < CAST(:as_of AS DATE))
  OR (pending AND days_to_close <= CAST(:days_before_closing AS INT))
  OR (signed AND estimated > 0 AND actual >= CAST(:actual_to_estimate_ratio AS DECIMAL(9, 2)) * estimated)
