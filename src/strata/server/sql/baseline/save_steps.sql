-- Saving a baseline: a copy of the saved version's planned dates, which stays when the plan reader
-- rebuilds silver.plan_steps. They carry the save's time, so a check reads only the steps of the save its
-- baseline row names, and the steps of an earlier save leave after the row has moved on.
INSERT INTO strata.ops.plan_baseline_steps
  (project_id, agency_id, document_id, activity_reference_no, step, step_order, planned_on, saved_at, public_from)
SELECT
  :project_id,
  :agency_id,
  document_id,
  activity_reference_no,
  step,
  step_order,
  planned_on,
  CAST(:saved_at AS TIMESTAMP),
  :public_from
FROM strata.silver.plan_steps
WHERE document_id = :document_id
