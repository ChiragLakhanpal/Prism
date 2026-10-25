-- A project's documents of one type that were public before a date, each numbered paragraph of their main
-- text with its passages (a long paragraph is divided into parts that share its number). An annex numbers
-- its paragraphs again from 1, so its paragraphs are left out: a citation such as "ICR para 11" means the
-- main text's (strata.knowledge.retrieval.labels).
SELECT passage_id, document_id, report_number, version, paragraph, section_path, public_from
FROM strata.gold.passage
WHERE project_id = :project_id
  AND document_type = :document_type
  AND public_from < :before
  AND (replaced_on IS NULL OR replaced_on >= :before)
  AND paragraph_numbered
  AND kind = 'paragraph'
  AND section_path NOT LIKE 'Annex%'
ORDER BY document_id, passage_id
