-- Every source every answer cited, for the answers that cite a different paragraph after a passage was ranked
-- lower (strata.knowledge.retrieval.reports).
SELECT run_id, query_kind, evidence_id, tool, project_id, asked_at
FROM strata.ops.answer_citations
ORDER BY asked_at, run_id
