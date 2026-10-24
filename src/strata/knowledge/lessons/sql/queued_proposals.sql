-- The proposals that already wait in, or went through, the review queue, so each is queued once.
SELECT i.proposal_id
FROM strata.ops.lesson_review_items AS i
WHERE i.kind = 'new'
