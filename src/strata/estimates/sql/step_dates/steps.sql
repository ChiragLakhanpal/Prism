-- The planned date for each STEP step (ticket 27): each step of each named activity in the newest plan version
-- public on the as-of date that lists it (ADR 0002), with the step's dates in that version, its first published
-- planned date and its delay, as strata.silver.plan_step_delays holds them. Delay is defined once, in
-- src/strata/lakehouse/sql/plans/plan_step_delays.sql (ticket 08), and never worked out again here. The activity's
-- Process Status comes from the same version. :references holds the STEP references, joined by commas.
--
-- When several versions list an activity, the newest by plan date wins, then the one disclosed last, as
-- find_comparables' package.sql picks a package's row. A step is matched by STEP's name, never by its place in
-- the table, which moves when a table has prequalification columns. The activity's STEP table (its section) picks
-- its method family.
WITH latest AS (
  SELECT r.document_id, r.activity_reference_no, r.section, r.process_status, v.plan_date
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE array_contains(split(:references, ','), r.activity_reference_no)
    AND v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
)
SELECT
  l.activity_reference_no,
  l.section,
  l.process_status,
  l.plan_date,
  d.step,
  d.step_order,
  d.planned_on,
  d.actual_on,
  d.first_planned_on,
  d.first_planned_plan_date,
  d.delay_days,
  d.first_listing_confirmed,
  d.public_from
FROM latest AS l
JOIN strata.silver.plan_step_delays AS d
  ON d.document_id = l.document_id
  AND d.activity_reference_no = l.activity_reference_no
WHERE d.public_from <= :as_of
ORDER BY l.activity_reference_no, d.step_order
