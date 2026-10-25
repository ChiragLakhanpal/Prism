-- The reports of the run's projects that the batch model reads assertions from: every version of each report
-- of the document types the evidence ladder's report tiers name (:document_types, joined by commas, which
-- no document type contains), with the day a later version replaced it (ticket 11's rule).
-- :every_project true reads every project at once (the nightly run, ticket 43); false reads the projects in
-- :projects, joined by commas, which no project id contains (one project's page).
SELECT
  d.document_id,
  d.project_id,
  d.document_type,
  d.report_number,
  d.version,
  d.document_date,
  d.replaced_on,
  d.public_from
FROM strata.silver.documents AS d
WHERE (:every_project OR array_contains(split(:projects, ','), d.project_id))
  AND array_contains(split(:document_types, ','), d.document_type)
ORDER BY d.document_date, d.document_id
