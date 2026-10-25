-- A project's Documents tab and source view: each document version the passage reader read, with its key
-- in the project and how many of its pages it read: a page of published text (Route A), or a page the
-- layout parser recovered a passage from (Route B).
SELECT
  d.document_id,
  d.document_type,
  d.report_number,
  d.version,
  d.document_date,
  d.disclosed_on,
  d.language,
  d.pdf_pages,
  d.pdf_url,
  d.replaced_on,
  d.doc_key,
  d.public_from,
  (SELECT count(*) FROM strata.silver.document_page_routes AS r
   WHERE r.document_id = d.document_id AND (r.route = 'A' OR r.passages > 0)) AS pages_read,
  (SELECT max(i.sequence) FROM strata.silver.isr_ratings AS i WHERE i.document_id = d.document_id) AS sequence
FROM strata.silver.documents AS d
WHERE d.project_id = :project_id
ORDER BY d.document_date, d.document_id
