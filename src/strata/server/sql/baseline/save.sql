-- Saving a baseline: who saved which version, and when.
INSERT INTO strata.ops.plan_baselines
  (project_id, agency_id, implementing_agency, document_id, plan_date, saved_by, saved_by_name, saved_at, public_from)
VALUES
  (:project_id, :agency_id, :implementing_agency, :document_id, :plan_date, :saved_by, :saved_by_name, :saved_at,
   :public_from)
