-- Every passage report and withdrawal, in the order they were written (strata.knowledge.retrieval.reports).
SELECT report_id, event, viewer_id, viewer_email, viewer_role, evidence_id, passage_id, project_id, run_id,
  sentence_index, sentence, question, query_kind, kind, reason, as_of, own_project, reported_at, public_from
FROM strata.ops.candidate_labels
ORDER BY reported_at, report_id, event DESC
