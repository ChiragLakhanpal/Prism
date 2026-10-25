-- The passages of the run's projects' ISRs that hold a key date by its label, such as Mid-Term Review Date, the
-- newest ISR first. Each ISR prints the project's key dates on its first page.
-- :every_project true reads every project at once (the nightly run, ticket 43); false reads the projects in
-- :projects, joined by commas, which no project id contains (one project's page).
SELECT
  p.project_id,
  p.passage_id,
  p.text,
  d.document_date
FROM strata.silver.passages AS p
JOIN strata.silver.documents AS d ON d.document_id = p.document_id
WHERE (:every_project OR array_contains(split(:projects, ','), p.project_id))
  AND d.document_type = :document_type
  AND instr(p.text, :label) > 0
ORDER BY p.project_id, d.document_date DESC, p.passage_id
