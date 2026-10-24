-- The evidence of every passing proposal, each with its passage's whole words, so a page can show the quote
-- in its paragraph.
SELECT
  e.proposal_id,
  e.role,
  e.passage_id,
  e.document_id,
  e.version,
  e.project_id,
  e.document_type,
  e.report_number,
  e.document_date,
  e.paragraph,
  e.cited_page,
  e.quote,
  e.restated_by_ieg,
  e.public_from,
  p.text AS passage_text,
  p.language
FROM strata.silver.lesson_evidence AS e
LEFT JOIN strata.silver.passages AS p ON p.passage_id = e.passage_id
ORDER BY e.proposal_id, e.role DESC, e.document_date, e.passage_id
