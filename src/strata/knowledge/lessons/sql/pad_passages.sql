-- The passages of a project's current Project Appraisal Document, where it names the procurement rules
-- the project follows (config/editions.toml).
SELECT p.text
FROM strata.silver.passages AS p
JOIN strata.silver.documents AS d ON d.document_id = p.document_id
WHERE d.project_id = :project_id
  AND d.document_type = 'Project Appraisal Document'
  AND d.replaced_on IS NULL
ORDER BY p.pdf_page, p.passage_id
