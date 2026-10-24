-- Every proposed lesson, with the quote check's outcome, and the day its report became public.
SELECT
  l.proposal_id,
  l.document_id,
  l.version,
  l.project_id,
  l.document_type,
  l.passage_id,
  l.paragraph,
  l.cited_page,
  l.statement,
  l.quote,
  l.risk_factors,
  l.stage,
  l.kind,
  l.edition_key,
  l.quote_check,
  l.proposed_on,
  d.public_from AS report_public_on
FROM strata.silver.lesson_proposals AS l
LEFT JOIN strata.silver.documents AS d ON d.document_id = l.document_id
ORDER BY l.proposal_id
