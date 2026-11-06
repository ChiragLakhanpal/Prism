-- The items one research run read (ticket 147), newest first. Read only after the run's row was found, since a run's
-- items are written before its row.
SELECT evidence_id, project_id, source_key, kind, source, title, text, url, published, date_known, observed,
       location, image_urls, author, read_on, public_from
FROM strata.ops.research_items
WHERE run_id = :run_id
ORDER BY public_from DESC, evidence_id
