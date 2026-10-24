-- Saving a baseline: a copy of the saved version's planned dates, which stays when the plan reader
-- rebuilds silver.plan_steps.
INSERT INTO strata.ops.plan_baseline_steps
  (project_id, agency_id, document_id, activity_reference_no, step, step_order, planned_on, public_from)
SELECT
  :project_id,
  :agency_id,
  document_id,
  activity_reference_no,
  step,
  step_order,
  planned_on,
  :public_from
FROM strata.silver.plan_steps
WHERE document_id = :document_id
