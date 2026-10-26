-- The showcase trail (Module 1): the paragraph of a completion report that the link scorer found appearing together
-- with one contract, with the highest score, and its PDF page (strata.gold.edge and strata.gold.passage, ticket 22).
SELECT
  p.paragraph AS paragraph,
  CAST(p.pdf_page AS STRING) AS page,
  p.document_id AS document_id,
  CAST(NULL AS STRING) AS run_id,
  CAST(:today AS DATE) AS measured_on
FROM strata.gold.edge AS e
JOIN strata.gold.passage AS p ON e.to_id = concat('strata.gold.passage:', p.passage_id)
WHERE e.kind = 'appeared_together' AND e.from_id = :contract AND p.document_type = :document_type
  AND p.paragraph_numbered
ORDER BY e.score DESC, p.passage_id
LIMIT 1
