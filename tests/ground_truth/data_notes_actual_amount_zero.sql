-- Two packages in the demo plan show an Actual Amount of 0.00, which Strata shows as a data note.
-- Source: .scratch/strata/spec.md, Testing Decisions, from the Northern Water Works Development
-- Agency's October 9, 2026 Procurement Plan for P156634.
-- expect: activity_reference_no
-- expect: KE-NWWDA-503455-CW-RFQ
-- expect: KE-NWWDA-541061-CW-RFQ
SELECT activity_reference_no
FROM strata.placeholder.plan_rows
WHERE actual_amount_usd = 0
ORDER BY activity_reference_no
