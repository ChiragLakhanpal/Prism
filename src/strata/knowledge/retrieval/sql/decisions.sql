-- Every act on a group of passage reports, oldest first (strata.knowledge.retrieval.reports).
SELECT decision_id, group_id, passage_id, query_kind, act, reason, reviewer_email, reviewer_name, report_ids,
  agreeing, label_weight, expected_state, decided_at, public_from
FROM strata.ops.label_decisions
ORDER BY decided_at, decision_id
