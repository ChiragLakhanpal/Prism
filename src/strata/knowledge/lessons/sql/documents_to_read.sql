-- The documents the lesson extractor reads: each current version of an evaluation report (the types in
-- :types, joined by commas) that the passage reader has read into passages.
SELECT
  d.document_id,
  d.version,
  d.project_id,
  d.document_type,
  d.report_number,
  d.language
FROM strata.silver.documents AS d
WHERE array_contains(split(:types, ','), d.document_type)
  AND d.replaced_on IS NULL
  AND EXISTS (SELECT 1 FROM strata.silver.passages AS p WHERE p.document_id = d.document_id)
ORDER BY d.project_id, d.document_id
