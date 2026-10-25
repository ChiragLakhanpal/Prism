-- The step backtest's test steps (ticket 27): each step of each activity, in the newest plan version public on
-- the as-of date (the test year's cutoff) that lists it, whose first published planned date falls from :year_from
-- up to :year_to and which that version shows not reached yet, with the activity's plan table and Method, which
-- pick its method family. Delay and the first published date are strata.silver.plan_step_delays' (ticket 08).
WITH latest AS (
  SELECT r.document_id, r.activity_reference_no, r.section, r.method, r.process_status
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
)
SELECT
  l.activity_reference_no,
  l.section,
  l.method,
  l.process_status,
  d.step,
  d.first_planned_on,
  d.public_from
FROM latest AS l
JOIN strata.silver.plan_step_delays AS d
  ON d.document_id = l.document_id
  AND d.activity_reference_no = l.activity_reference_no
WHERE d.public_from <= :as_of
  AND d.first_planned_on >= CAST(:year_from AS DATE)
  AND d.first_planned_on < CAST(:year_to AS DATE)
  AND d.actual_on IS NULL
  AND (l.process_status IS NULL OR l.process_status <> 'Canceled')
ORDER BY l.activity_reference_no, d.step_order
