-- The Northern Water Works Development Agency's track record against its plans, as agency_track_record counts it
-- for its Procurement Plan of October 9, 2026 (ticket 36): of the plan's nine activities, seven show a signed
-- contract (Process Status Signed or Completed) and two, KE-NWWDA-541055-CW-RFB and KE-NWWDA-541062-CW-RFQ, are
-- Pending Implementation (tests/ground_truth/values.toml, [[plan_row]] process_status, and [plan] also_lists for
-- KE-NWWDA-207796-CS-INDV, Completed). Each of the seven was signed after the date its first published plan gave
-- for signing, so none was signed by it and all seven count as late at late_days = 0 (KE-NWWDA-229129-CW-RFB,
-- 186 days: plan-229129-days-late). Both pending activities' planned signing dates passed before the plan's
-- date, so they count as open past their date. The awards dataset shows both signed (award-541055-signed,
-- award-541062-signed); the tool counts the plan's own signed dates and lists the two as differing.
-- engines: duckdb, databricks
-- param: document_id = 40132287
-- param: as_of = 2026-10-22
-- param: late_days = 0
-- expect: n,signed_by_plan,signed_late,open_past_date
-- expect: 7,0,7,2
SELECT
  count(CASE WHEN d.actual_on IS NOT NULL AND d.first_planned_on IS NOT NULL THEN 1 END) AS n,
  count(CASE WHEN d.actual_on IS NOT NULL AND d.delay_days <= 0 THEN 1 END) AS signed_by_plan,
  count(CASE WHEN d.actual_on IS NOT NULL AND d.delay_days > CAST(:late_days AS INT) THEN 1 END) AS signed_late,
  count(CASE WHEN d.actual_on IS NULL AND d.first_planned_on < CAST(:as_of AS DATE) THEN 1 END) AS open_past_date
FROM strata.silver.plan_step_delays AS d
WHERE d.document_id = :document_id
  AND d.step = 'Signed Contract'
  AND d.public_from <= CAST(:as_of AS DATE)
