-- One act on the lesson review queue, added only while the item holds no act of the same kind, so two people
-- acting on the same stage at once can't both write it: the second finds the first and is told the item moved
-- on (src/strata/knowledge/lessons/review.py, LessonReview.act). The app writes it as its own service principal.
INSERT INTO strata.ops.lesson_review_acts (act_id, item_id, act, stage, outcome, repeat_of, change, reason, actor,
  actor_name, actor_role, actor_region, acted_at, public_from)
SELECT
  :act_id,
  :item_id,
  :act,
  :stage,
  :outcome,
  CAST(:repeat_of AS STRING),
  CAST(:change AS STRING),
  CAST(:reason AS STRING),
  :actor,
  :actor_name,
  :actor_role,
  :actor_region,
  :acted_at,
  :public_from
FROM (SELECT 1 AS one) AS once
WHERE NOT EXISTS (
  SELECT 1 FROM strata.ops.lesson_review_acts AS a WHERE a.item_id = :item_id AND a.act = :act
)
