-- The acts that change how a passage ranks for one kind of question, made by a date, oldest first
-- (strata.knowledge.retrieval.demotion). The latest of a group decides whether its passage ranks lower.
SELECT group_id, passage_id, act, decided_at, public_from
FROM strata.ops.label_decisions
WHERE query_kind = :query_kind
  AND public_from <= :as_of
  AND act IN ('accepted', 'accepted_by_agreement', 'audit', 'left_lower', 'declined', 'restored', 'reopened')
ORDER BY decided_at, decision_id
