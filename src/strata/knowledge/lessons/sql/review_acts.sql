-- Every act on the lesson review queue, in the order people took them: a recommendation comes before the
-- decision on it, even when both were written in the same instant.
SELECT
  a.act_id,
  a.item_id,
  a.act,
  a.stage,
  a.outcome,
  a.repeat_of,
  a.change,
  a.reason,
  a.actor,
  a.actor_name,
  a.actor_role,
  a.actor_region,
  a.acted_at
FROM strata.ops.lesson_review_acts AS a
ORDER BY a.acted_at, CASE a.act WHEN 'recommend' THEN 0 WHEN 'decide' THEN 1 ELSE 2 END, a.act_id
