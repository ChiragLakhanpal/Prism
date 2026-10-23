-- check_plan: the data notes on one plan version's rows. src/strata/lakehouse/sql/plans/plan_data_notes.sql
-- defines each note once; the tool only reads them.
SELECT
  activity_reference_no,
  note,
  reference_method_code,
  reference_method,
  method,
  process_status,
  actual_amount_usd
FROM strata.silver.plan_data_notes
WHERE document_id = :document_id
  AND public_from <= :as_of
ORDER BY activity_reference_no, note
