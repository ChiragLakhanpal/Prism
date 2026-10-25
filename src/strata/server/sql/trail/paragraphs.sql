-- The paragraphs that appeared together with an activity's contracts (ticket 22): each appeared_together edge
-- from one of the contracts (:contracts, evidence ids joined by commas) that was public on the as-of date, with
-- its paragraph as it was then: public, and not yet replaced by a re-issue of its report (ADR 0002). Oldest
-- document first, then by paragraph, so the order ranks nothing.
SELECT
  e.from_id AS contract_evidence_id,
  e.to_id AS evidence_id,
  e.score,
  e.mentions,
  e.category,
  e.sector_code,
  e.sector_name,
  e.public_from AS link_public_from,
  p.passage_id,
  p.document_id,
  p.document_type,
  p.document_date,
  p.project_id,
  p.section_path,
  p.paragraph,
  p.paragraph_numbered,
  p.pdf_page,
  p.printed_page,
  p.doc_key,
  p.language,
  p.text,
  p.public_from
FROM strata.gold.edge AS e
JOIN strata.gold.passage AS p ON e.to_id = concat('strata.gold.passage:', p.passage_id)
WHERE e.kind = 'appeared_together'
  AND array_contains(split(:contracts, ','), e.from_id)
  AND e.public_from <= :as_of
  AND p.public_from <= :as_of
  AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)
ORDER BY p.document_date, p.document_id, p.passage_id, e.from_id
