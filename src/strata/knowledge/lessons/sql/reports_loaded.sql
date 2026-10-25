-- The completion reports and IEG's reports Strata first fetched in a window, for the Lessons page's opening sentence
-- (strata.knowledge.lessons.page): each document of a type in :types (joined by commas) whose published text Strata
-- first fetched at or after :since and before :until, with its project.
SELECT
  d.document_id,
  d.project_id,
  d.document_type,
  d.doc_key,
  d.disclosed_on,
  p.project_name,
  f.first_fetched_at
FROM strata.silver.documents AS d
JOIN (SELECT t.document_id, min(t.fetched_at) AS first_fetched_at
      FROM strata.bronze.document_texts AS t
      GROUP BY t.document_id) AS f ON f.document_id = d.document_id
LEFT JOIN strata.gold.project AS p ON p.project_id = d.project_id
WHERE array_contains(split(:types, ','), d.document_type)
  AND f.first_fetched_at >= :since
  AND f.first_fetched_at < :until
ORDER BY f.first_fetched_at, d.document_id
