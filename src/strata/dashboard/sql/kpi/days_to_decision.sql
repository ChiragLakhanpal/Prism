-- KPI days_to_decision (config/kpis.toml), the knowledge loop's leading indicator: one row per proposed lesson a lead
-- procurement specialist decided in the dates chosen, with the calendar days from its report's publication to the
-- decision, as the lesson review stored them on each lesson's first version (strata.ops.lesson_versions,
-- days_from_publication; ticket 29). The report is the document type the lesson's proposal cites, with its project.
-- Newest first. The dots of tile 21 and the rows of tile 24 are these rows.
SELECT
  v.decided_on,
  v.published_on,
  v.days_from_publication,
  v.project_id,
  CASE WHEN d.document_type IS NULL THEN v.project_id ELSE concat(d.document_type, ', ', v.project_id) END AS report
FROM strata.ops.lesson_versions AS v
LEFT JOIN strata.ops.lesson_review_items AS i ON i.item_id = v.item_id
LEFT JOIN (
  SELECT DISTINCT document_id, document_type
  FROM strata.gold.passage
) AS d ON i.proposal_id LIKE concat(d.document_id, '/%')
WHERE v.version = 1
  AND v.days_from_publication IS NOT NULL
  AND v.decided_on BETWEEN :date_from AND :date_to
ORDER BY v.decided_on DESC, v.lesson_id
