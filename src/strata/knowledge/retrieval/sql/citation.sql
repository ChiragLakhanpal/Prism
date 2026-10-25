-- The sentences of one answer that cite one source, with the question the answer answered
-- (strata.knowledge.retrieval.reports): a passage report takes its question and sentence from here, never from
-- the browser.
SELECT run_id, viewer_id, question, query_kind, as_of, view, sentence_index, sentence, evidence_id, tool,
  project_id, asked_at, public_from
FROM strata.ops.answer_citations
WHERE run_id = :run_id
  AND evidence_id = :evidence_id
ORDER BY sentence_index
