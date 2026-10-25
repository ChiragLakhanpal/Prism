-- The latest build of the labeled set: every label it wrote (strata.knowledge.retrieval.labels).
SELECT build_id, query_set, query_id, query_text, query_date, project_id, passage_id, grade, origin, weight, public_from
FROM strata.ops.retrieval_labels
WHERE build_id = (
  SELECT build_id FROM strata.ops.retrieval_label_builds ORDER BY built_at DESC, build_id DESC LIMIT 1
)
ORDER BY query_set, query_id, passage_id
