-- A project's Connections tab (ticket 22): each appeared_together edge of the project that was public on the as-of
-- date, from a contract with a STEP reference to a passage as it was then: public, and not yet replaced by a
-- re-issue of its report (ADR 0002). Strongest first.
SELECT
  c.step_reference,
  c.contract_id,
  e.to_id AS evidence_id,
  e.score,
  e.scored_on,
  p.passage_id,
  p.document_id,
  p.document_type,
  p.document_date,
  p.paragraph,
  p.paragraph_numbered,
  p.section_path
FROM strata.gold.edge AS e
JOIN strata.gold.contract AS c ON e.from_id = concat('strata.gold.contract:', c.contract_id)
JOIN strata.gold.passage AS p ON e.to_id = concat('strata.gold.passage:', p.passage_id)
WHERE e.kind = 'appeared_together'
  AND e.project_id = :project_id
  AND c.step_reference IS NOT NULL
  AND e.public_from <= :as_of
  AND p.public_from <= :as_of
  AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)
ORDER BY e.score DESC, c.step_reference, p.passage_id
