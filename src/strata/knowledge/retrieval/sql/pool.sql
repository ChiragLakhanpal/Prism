-- Every passage pooled for a notice query (strata.knowledge.retrieval.judging).
SELECT query_id, passage_id
FROM strata.ops.retrieval_pool
ORDER BY query_id, passage_id
