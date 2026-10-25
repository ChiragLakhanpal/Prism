-- A project's timeline (ticket 23): every report Strata read for the project, each version of it public on the
-- as-of date (ADR 0002), oldest first. A version a later one replaced by then is drawn as replaced.
SELECT
  d.document_id,
  d.document_type,
  d.report_number,
  d.version,
  d.document_date,
  d.replaced_on,
  d.pdf_pages,
  d.doc_key,
  d.public_from
FROM strata.silver.documents AS d
WHERE d.project_id = :project_id
  AND d.public_from <= :as_of
ORDER BY d.document_date, d.version, d.document_id
