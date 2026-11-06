-- A project's timeline (ticket 23): every report Prism read for the project, each version of it public on the
-- as-of date (ADR 0002), oldest first. A version a later one replaced by then is drawn as replaced. A report Prism
-- read in two languages is drawn once, in :language when it has that version. An ISR carries
-- the sequence number its first page prints (strata.silver.isr_ratings), so it keeps its name when get_disagreements,
-- which gives the ratings, does not answer.
SELECT
  d.document_id,
  d.document_type,
  d.report_number,
  d.version,
  d.document_date,
  d.replaced_on,
  d.pdf_pages,
  d.doc_key,
  d.public_from,
  s.sequence
FROM strata.silver.documents AS d
LEFT JOIN (
  SELECT r.document_id, max(r.sequence) AS sequence
  FROM strata.silver.isr_ratings AS r
  WHERE r.project_id = :project_id
  GROUP BY r.document_id
) AS s
  ON s.document_id = d.document_id
WHERE d.project_id = :project_id
  AND d.public_from <= :as_of
QUALIFY row_number() OVER (
  PARTITION BY coalesce(d.report_number, d.document_id), d.version
  ORDER BY CASE WHEN d.language = :language THEN 0 ELSE 1 END, d.document_id
) = 1
ORDER BY d.document_date, d.version, d.document_id
