-- When each source was first opened in the evidence drawer, by anyone (strata.ops.evidence_opened keeps one row
-- per viewer and source), for "Wrong passage" reports per 100 sources opened (strata.knowledge.retrieval.reports).
SELECT first_opened_at
FROM strata.ops.evidence_opened
