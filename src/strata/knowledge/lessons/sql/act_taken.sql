-- Which act of one kind an item holds: after insert_act.sql, the act that was written first.
SELECT a.act_id
FROM strata.ops.lesson_review_acts AS a
WHERE a.item_id = :item_id AND a.act = :act
ORDER BY a.acted_at, a.act_id
