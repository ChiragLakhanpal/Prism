-- The ICR Reviews' passages that cite the ICR by paragraph ("ICR para 54"), in every version, oldest first,
-- so a re-issue under the same report number adds no second query (strata.knowledge.retrieval.labels).
SELECT passage_id, document_id, project_id, report_number, version, part, text, public_from
FROM strata.gold.passage
WHERE document_type = :review_type
  AND text LIKE :marker
ORDER BY report_number, public_from, version, passage_id
