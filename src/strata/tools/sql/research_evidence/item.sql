-- One research item by its evidence id, as the latest finished run kept it, when it was public by the as-of day: the
-- evidence drawer's reader for strata.research.item (src/strata/server/evidence.py).
SELECT i.evidence_id, i.source, i.kind, i.title, i.text, i.url, i.published, i.date_known, i.observed, i.location,
       i.image_urls, i.author, i.read_on, i.public_from
FROM strata.ops.research_items AS i
JOIN strata.ops.research_runs AS r ON r.run_id = i.run_id
WHERE i.evidence_id = :evidence_id
  AND i.public_from <= :as_of
  AND r.finished IS NOT NULL
ORDER BY r.finished DESC
LIMIT 1
