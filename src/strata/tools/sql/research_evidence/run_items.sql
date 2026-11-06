-- research_evidence: every item one run kept, in the one item shape (ticket 147), newest first, then by evidence id.
-- The adapter leaves out an item made public after the call's date (public_by_as_of false) and says so in the
-- coverage line.
SELECT evidence_id, source_key, kind, source, title, text, url, published, date_known, observed, location,
       image_urls, author, read_on, public_from, public_from <= :as_of AS public_by_as_of
FROM strata.ops.research_items
WHERE run_id = :run_id
ORDER BY public_from DESC, evidence_id
