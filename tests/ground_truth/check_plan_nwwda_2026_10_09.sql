-- The plan check's counts for the Northern Water Works Development Agency's Procurement Plan of
-- October 9, 2026 for P156634, as of October 22, 2026, with each check written as plain SQL over the
-- plan reader's tables, apart from check_plan's own code (src/strata/tools/check_plan.py). A row is
-- counted under its strongest mark: needs a look, then watch, then moved on since the plan, then data note.
--
-- The expected counts are the marks the blueprint's Check a plan wireframe gives the plan's eight
-- activities (tests/ground_truth/values.toml, each plan_row's wireframe_mark), plus the ninth
-- activity the wireframe leaves out, KE-NWWDA-207796-CS-INDV (values.toml, plan.also_lists), which
-- has no mark, except the two the wireframe marks as pending with no contract: the contract awards say
-- KE-NWWDA-541055-CW-RFB was signed on June 22, 2026 and KE-NWWDA-541062-CW-RFQ on May 11, 2026
-- (values.toml, award-541055-signed and award-541062-signed), before this plan's date, so the records have
-- moved past the plan (ticket 132): one worth watching, two moved on, three data notes and three with no mark.
-- This is the agency's latest plan, so a contract record or an award notice that signed the contract and was
-- public by the as-of date is one the plan missed.
--
-- The thresholds are config/thresholds.toml's [plan_check] values. Changing one there means
-- changing it here in the same change (CLAUDE.md rule 4).
-- param: agency = Northern Water Works Development Agency
-- param: plan_date = 2026-10-09
-- param: as_of = 2026-10-22
-- param: completion_passed_min_estimated_usd = 1000000
-- param: days_before_closing = 90
-- param: actual_to_estimate_ratio = 2.0
-- param: awards = awards
-- param: awards_before_2017 = awards_fy2001_2016
-- param: award_notice = Contract Award
-- expect: mark,activities
-- expect: data note,3
-- expect: moved on,2
-- expect: none,3
-- expect: watch,1
WITH signed_records AS (
  SELECT c.step_reference
  FROM strata.gold.contract AS c
  WHERE c.source IN (:awards, :awards_before_2017)
    AND c.contract_signing_date IS NOT NULL
    AND c.public_from <= CAST(:as_of AS DATE)
  UNION ALL
  SELECT n.step_reference
  FROM strata.gold.notice AS n
  WHERE n.notice_type = :award_notice
    AND n.contract_signature_date IS NOT NULL
    AND n.public_from <= CAST(:as_of AS DATE)
),
activity AS (
  SELECT
    r.estimated_amount_usd AS estimated,
    r.actual_amount_usd AS actual,
    sc.actual_on IS NOT NULL OR r.process_status IN ('Signed', 'Completed') AS signed,
    sc.actual_on IS NULL
      AND COALESCE(r.process_status, 'Pending Implementation')
        IN ('Pending Implementation', 'Under Implementation', 'Under Review', 'Draft') AS pending,
    COALESCE(cc.first_planned_on, cc.planned_on) AS planned_completion,
    datediff(p.closing_date, CAST(:as_of AS DATE)) AS days_to_close,
    EXISTS (
      SELECT 1
      FROM strata.silver.plan_data_notes AS n
      WHERE n.document_id = r.document_id AND n.activity_reference_no = r.activity_reference_no
    ) AS noted,
    r.process_status IN ('Pending Implementation', 'Under Implementation', 'Under Review', 'Draft')
      AND sc.actual_on IS NULL
      AND EXISTS (SELECT 1 FROM signed_records AS s WHERE s.step_reference = r.activity_reference_no) AS moved_on
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
),
marked AS (
  SELECT
    CASE
      WHEN moved_on THEN 'moved on'
      WHEN pending
        AND (estimated IS NULL OR estimated >= CAST(:completion_passed_min_estimated_usd AS DECIMAL(18, 2)))
        AND planned_completion < CAST(:as_of AS DATE) THEN 'needs a look'
      WHEN pending AND days_to_close <= CAST(:days_before_closing AS INT) THEN 'watch'
      WHEN signed AND estimated > 0
        AND actual >= CAST(:actual_to_estimate_ratio AS DECIMAL(9, 2)) * estimated THEN 'watch'
      WHEN noted THEN 'data note'
      ELSE 'none'
    END AS mark
  FROM activity
)
SELECT mark, count(*) AS activities
FROM marked
GROUP BY mark
ORDER BY mark
