-- The passages of a project's ISRs that hold a key date by its label, such as Mid-Term Review Date, the
-- newest ISR first. Each ISR prints the project's key dates on its first page.
SELECT
  p.passage_id,
  p.text,
  d.document_date
FROM strata.silver.passages AS p
JOIN strata.silver.documents AS d ON d.document_id = p.document_id
WHERE p.project_id = :project_id
  AND d.document_type = :document_type
  AND instr(p.text, :label) > 0
ORDER BY d.document_date DESC, p.passage_id
