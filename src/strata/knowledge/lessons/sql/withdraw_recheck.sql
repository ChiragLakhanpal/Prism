-- A re-check this request wrote after another reviewer's landed first, taken back so the lesson keeps one open
-- re-check. A warehouse runs insert_recheck.sql without a transaction, so two requests can both find none open and
-- both write one; open_recheck.sql then names the first, and the later request removes its own row by its item id
-- before it answers 409 recheck_open (src/strata/knowledge/lessons/review.py, LessonReview.recheck).
DELETE FROM strata.ops.lesson_review_items
WHERE item_id = :item_id
  AND kind = 'recheck'
