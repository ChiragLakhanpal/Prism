-- check_plan: every published version of a project's Procurement Plans, for the tool to choose one.
-- It returns them all, also those disclosed after the as-of date, so the tool can say why it cannot
-- use a version the caller named (ADR 0002); it never checks a version that was not public then.
SELECT
  document_id,
  project_id,
  implementing_agency,
  plan_date,
  disclosed_on,
  text_url,
  pdf_url,
  public_from
FROM strata.silver.plan_versions
WHERE project_id = :project_id
ORDER BY plan_date, public_from, document_id
