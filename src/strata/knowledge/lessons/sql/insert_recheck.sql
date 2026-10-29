-- A re-check of a lesson asked for by a lesson reviewer, added only while the lesson has no open re-check (one no
-- lead has decided), so two people asking at once can't both open one: the second finds the first and is told a
-- re-check is open (src/strata/knowledge/lessons/review.py, LessonReview.recheck). The app writes it as its own
-- service principal.
INSERT INTO strata.ops.lesson_review_items (item_id, kind, proposal_id, lesson_id, version, decided_item_id,
  project_id, region, decided_region, origin, origin_by, origin_by_name, origin_reason, origin_item_id, entered_on,
  due_on, created_at, public_from)
SELECT
  :item_id,
  'recheck',
  CAST(NULL AS STRING),
  :lesson_id,
  :version,
  CAST(NULL AS STRING),
  :project_id,
  :region,
  CAST(NULL AS STRING),
  'asked',
  :origin_by,
  :origin_by_name,
  :origin_reason,
  CAST(NULL AS STRING),
  :entered_on,
  CAST(NULL AS DATE),
  :created_at,
  :public_from
FROM (SELECT 1 AS one) AS once
WHERE NOT EXISTS (
  SELECT 1
  FROM strata.ops.lesson_review_items AS i
  WHERE i.lesson_id = :lesson_id
    AND i.kind = 'recheck'
    AND NOT EXISTS (
      SELECT 1 FROM strata.ops.lesson_review_acts AS a WHERE a.item_id = i.item_id AND a.act = 'decide'
    )
)
