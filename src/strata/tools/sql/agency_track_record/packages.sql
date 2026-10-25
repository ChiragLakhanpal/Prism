-- agency_track_record: each activity of one Procurement Plan version with its Signed Contract step, the date its
-- first published plan gave for that step and its delay, from strata.silver.plan_step_delays, the one place that
-- defines delay (src/strata/lakehouse/sql/plans/plan_step_delays.sql). It never measures delay itself. Only rows
-- public by the as-of date (ADR 0002). An activity the version lists with no Signed Contract step still comes
-- back, with no dates, so the tool can say it could not be measured.
SELECT
  r.activity_reference_no,
  r.description,
  r.section,
  r.method,
  r.process_status,
  r.estimated_amount_usd,
  r.pdf_page,
  d.first_planned_on,
  d.first_planned_plan_date,
  d.first_listing_confirmed,
  d.actual_on,
  d.delay_days,
  GREATEST(r.public_from, coalesce(d.public_from, r.public_from)) AS public_from
FROM strata.silver.plan_rows AS r
LEFT JOIN strata.silver.plan_step_delays AS d
  ON d.document_id = r.document_id
  AND d.activity_reference_no = r.activity_reference_no
  AND d.step = 'Signed Contract'
  AND d.public_from <= :as_of
WHERE r.document_id = :document_id
  AND r.public_from <= :as_of
ORDER BY r.activity_reference_no
