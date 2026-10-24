-- Which of a draft's sources this viewer opened in the evidence drawer since :since, the moment the draft
-- was saved, wherever they opened it (the 35 brief, section 2), and when they last did. ticket 14's
-- strata.ops.evidence_opened keeps one row per viewer and source. :ids holds the evidence ids joined by
-- commas, which no evidence id contains.
SELECT evidence_id, last_opened_at
FROM strata.ops.evidence_opened
WHERE viewer_id = :viewer_id
  AND array_contains(split(:ids, ','), evidence_id)
  AND last_opened_at >= CAST(:since AS TIMESTAMP)
