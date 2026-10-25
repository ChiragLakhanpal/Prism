-- The labeled set's latest build, as the replay harness may read it: each label known by the date it is
-- frozen at (strata.estimates.retrieval).
SELECT query_set, query_id, query_text, query_date, project_id, passage_id, grade, origin, weight, public_from
FROM strata.ops.retrieval_labels
WHERE public_from <= :as_of
  AND build_id = (
    SELECT build_id FROM strata.ops.retrieval_label_builds ORDER BY built_at DESC, build_id DESC LIMIT 1
  )
ORDER BY query_set, query_id, passage_id
