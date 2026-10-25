-- check_plan on an upload (ticket 38): for each activity of the project that a published plan lists, each step's
-- planned date as first published, which an upload's delay is measured from, as a published plan's is
-- (silver.plan_step_delays, the one definition of delay). An activity no published plan lists has no row, and
-- its delay is measured from the upload's own dates. Only rows public by the as-of date count (ADR 0002).
SELECT
  d.activity_reference_no,
  d.step,
  min(d.first_planned_on) AS first_planned_on,
  min(d.first_planned_plan_date) AS first_planned_plan_date,
  bool_or(d.first_listing_confirmed) AS first_listing_confirmed,
  max(d.public_from) AS public_from
FROM strata.silver.plan_step_delays AS d
WHERE d.project_id = :project_id
  AND d.public_from <= :as_of
GROUP BY d.activity_reference_no, d.step
