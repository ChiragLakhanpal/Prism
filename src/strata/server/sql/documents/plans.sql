-- A project's Documents tab and source view: each Procurement Plan version the plan reader holds, with its
-- agency, read from the plan's text, and whether the layout parser read its STEP tables.
SELECT
  v.document_id,
  v.implementing_agency,
  v.plan_date,
  v.disclosed_on,
  v.pdf_pages,
  v.pdf_url,
  v.parse_reason,
  v.public_from
FROM strata.silver.plan_versions AS v
WHERE v.project_id = :project_id
ORDER BY v.plan_date, v.document_id
