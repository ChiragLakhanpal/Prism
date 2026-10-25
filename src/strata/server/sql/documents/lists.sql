-- A project's Documents tab (the 21 brief, section 6): every response of the documents API listing the
-- project's documents, oldest fetch first, so the newest list of each address wins.
SELECT
  url,
  response,
  fetched_at
FROM strata.bronze.document_lists
WHERE project_id = :project_id
ORDER BY fetched_at
