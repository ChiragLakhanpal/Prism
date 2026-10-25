-- The notice queries loaded for judging, each at its latest load (strata.knowledge.retrieval.judging).
SELECT query_id, n, query_text, notice_id, notice_ref, notice_date, project_id, judges, loaded_at
FROM strata.ops.retrieval_queries
ORDER BY n, loaded_at
