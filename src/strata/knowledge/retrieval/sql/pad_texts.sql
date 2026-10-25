-- Each PAD the passage reader holds, with its whole published text, so the labels can find the section
-- headed "Lessons Learned and Reflected in the Project Design" (strata.knowledge.retrieval.labels).
SELECT p.document_id, p.project_id, p.report_number, p.public_from, t.text
FROM (
  SELECT DISTINCT document_id, project_id, report_number, public_from
  FROM strata.gold.passage
  WHERE document_type = :pad_type
) AS p
JOIN strata.bronze.document_texts AS t ON t.document_id = p.document_id
ORDER BY p.project_id, p.public_from, p.document_id
