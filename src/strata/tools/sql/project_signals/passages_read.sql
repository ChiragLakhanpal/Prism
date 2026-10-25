-- project_signals: how many passages of one ISR were read by the as-of date, so an ISR that lists no
-- restructuring is told apart from one that was never read.
SELECT
  count(*) AS passages,
  max(p.public_from) AS public_from
FROM strata.gold.passage AS p
WHERE p.document_id = :document_id
  AND p.public_from <= :as_of
