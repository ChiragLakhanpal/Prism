-- What changed in a plan: the planned date of every STEP step of two versions' activities.
SELECT
  document_id,
  activity_reference_no,
  step,
  step_order,
  planned_on
FROM strata.silver.plan_steps
WHERE document_id IN (:now, :was)
ORDER BY document_id, activity_reference_no, step_order, step
