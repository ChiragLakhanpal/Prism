-- What changed in a plan (the 21 brief, section 5.4): every published version of a project's
-- Procurement Plans, with the agency's version just before each one and whether the layout parser
-- read its tables (parse_reason), so the route can say when the version before was listed but not read.
SELECT
  v.document_id,
  v.implementing_agency,
  v.plan_date,
  v.disclosed_on,
  v.previous_document_id,
  v.parse_reason,
  v.public_from,
  (SELECT count(*) FROM strata.silver.plan_rows AS r WHERE r.document_id = v.document_id) AS activities
FROM strata.silver.plan_versions AS v
WHERE v.project_id = :project_id
ORDER BY v.plan_date, v.public_from, v.document_id
