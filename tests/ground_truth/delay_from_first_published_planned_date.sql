-- Delay is measured from the first published planned date. KE-NWWDA-229129-CW-RFB was first listed
-- in the plan of April 21, 2021, which planned its signed contract for July 1, 2021; the October 9,
-- 2026 plan shows it signed January 3, 2022, 186 days later, at US$1,245,092.76. Source:
-- tests/ground_truth/values.toml, plan-229129-first-planned-signing, plan-229129-signed,
-- plan-229129-days-late and plan-229129-actual. ops/bundle/check.py same-rows checks it on the SQL
-- warehouse after the live plan run (ops/plans/run_live.py) has read the plans there.
-- engines: duckdb, databricks
-- param: reference = KE-NWWDA-229129-CW-RFB
-- param: plan_date = 2026-10-09
-- expect: first_planned_plan_date,first_planned_on,actual_on,delay_days,actual_amount_usd
-- expect: 2021-04-21,2021-07-01,2022-01-03,186,1245092.76
SELECT d.first_planned_plan_date, d.first_planned_on, d.actual_on, d.delay_days, r.actual_amount_usd
FROM strata.silver.plan_step_delays AS d
JOIN strata.silver.plan_versions AS v ON v.document_id = d.document_id
JOIN strata.silver.plan_rows AS r
  ON r.document_id = d.document_id AND r.activity_reference_no = d.activity_reference_no
WHERE d.activity_reference_no = :reference
  AND d.step = 'Signed Contract'
  AND v.plan_date = CAST(:plan_date AS DATE)
