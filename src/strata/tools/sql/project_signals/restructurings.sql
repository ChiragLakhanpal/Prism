-- project_signals: the passages of one ISR, public by the as-of date, that hold its restructuring history,
-- such as "Restructuring Level 2 Approved on 23-Jun-2026".
SELECT
  p.passage_id,
  p.text,
  p.pdf_page,
  p.public_from
FROM strata.gold.passage AS p
WHERE p.document_id = :document_id
  AND p.public_from <= :as_of
  AND p.text LIKE '%Restructuring Level%'
ORDER BY p.passage_id
