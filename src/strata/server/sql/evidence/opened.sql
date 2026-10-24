-- Which of an answer's sources this viewer has opened in the evidence drawer (ticket 14), so their
-- citation markers show the visited state when the answer lands. :ids holds the evidence ids joined by
-- commas, which no evidence id contains (src/strata/server/evidence.py leaves out any that does).
SELECT evidence_id
FROM strata.ops.evidence_opened
WHERE viewer_id = :viewer_id
  AND array_contains(split(:ids, ','), evidence_id)
