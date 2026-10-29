-- The open re-check of a lesson, after insert_recheck.sql: the one written first that no lead has decided yet.
SELECT i.item_id, i.entered_on
FROM strata.ops.lesson_review_items AS i
WHERE i.lesson_id = :lesson_id
  AND i.kind = 'recheck'
  AND NOT EXISTS (
    SELECT 1 FROM strata.ops.lesson_review_acts AS a WHERE a.item_id = i.item_id AND a.act = 'decide'
  )
ORDER BY i.created_at, i.item_id
