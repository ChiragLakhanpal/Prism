-- check_plan: the baseline a World Bank staff member saved for this agency's plans (strata.ops.plan_baselines),
-- once it was saved by the as-of date (ADR 0002), with the planned dates of the steps check_plan measures
-- delay on in the saved version. An activity the saved version did not list has no rows here.
SELECT
  b.document_id,
  b.implementing_agency,
  b.plan_date,
  b.saved_by_name,
  b.public_from,
  s.activity_reference_no,
  s.step,
  s.planned_on
FROM strata.ops.plan_baselines AS b
LEFT JOIN strata.ops.plan_baseline_steps AS s
  ON s.project_id = b.project_id
  AND s.agency_id = b.agency_id
  AND s.document_id = b.document_id
  AND s.step IN ('Signed Contract', 'Contract Completion')
WHERE b.project_id = :project_id
  AND b.agency_id = :agency_id
  AND b.public_from <= :as_of
ORDER BY s.activity_reference_no, s.step
