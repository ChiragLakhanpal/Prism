-- Two packages in the demo plan are Signed or Completed with an Actual Amount of 0.00, which
-- Strata shows as a data note. Source: tests/ground_truth/values.toml, plan-503455-actual-zero and
-- plan-541061-actual-zero, from page 3 of the Northern Water Works Development Agency's
-- October 9, 2026 Procurement Plan for P156634. The plan reader writes the notes
-- (src/strata/lakehouse/sql/plans/plan_data_notes.sql). The live plan run checks it on the SQL
-- warehouse once the workspace holds the plans (ops/plans/run_live.py).
-- param: agency = Northern Water Works Development Agency
-- param: plan_date = 2026-10-09
-- expect: activity_reference_no,process_status,actual_amount_usd
-- expect: KE-NWWDA-503455-CW-RFQ,Signed,0.00
-- expect: KE-NWWDA-541061-CW-RFQ,Completed,0.00
SELECT n.activity_reference_no, n.process_status, n.actual_amount_usd
FROM strata.silver.plan_data_notes AS n
JOIN strata.silver.plan_versions AS v ON v.document_id = n.document_id
WHERE v.implementing_agency = :agency
  AND v.plan_date = CAST(:plan_date AS DATE)
  AND n.note = 'actual_amount_zero'
ORDER BY n.activity_reference_no
