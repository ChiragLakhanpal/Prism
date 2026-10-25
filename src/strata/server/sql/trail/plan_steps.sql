-- The contract trail's plan stage (ticket 22): each STEP step one plan version gives an activity, with its
-- planned date as first published (the activity's first listing, silver.plan_step_delays) and its actual date
-- in this version. A step with neither date is left out.
SELECT
  step,
  step_order,
  first_planned_on,
  first_planned_plan_date,
  actual_on
FROM strata.silver.plan_step_delays
WHERE document_id = :document_id
  AND activity_reference_no = :reference
  AND (first_planned_on IS NOT NULL OR planned_on IS NOT NULL OR actual_on IS NOT NULL)
ORDER BY step_order
