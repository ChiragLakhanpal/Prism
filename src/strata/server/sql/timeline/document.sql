-- The evidence drawer's document view (ticket 23): one version of a report Strata read, by its documents API id,
-- public on the as-of date (ADR 0002).
SELECT
  d.document_id,
  d.project_id,
  d.document_type,
  d.report_number,
  d.version,
  d.document_date,
  d.replaced_on,
  d.pdf_pages,
  d.doc_key,
  d.public_from
FROM strata.silver.documents AS d
WHERE d.document_id = :document_id
  AND d.public_from <= :as_of
