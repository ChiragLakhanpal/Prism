-- The text of one PDF page of a document that the published text does not divide into pages: what the
-- layout parser read from it (Route B), else the PDF's own text layer, each from its newest reading.
SELECT text
FROM (
  SELECT l.text, 1 AS preference, l.parsed_at AS read_at
  FROM strata.bronze.layout_pages AS l
  WHERE l.document_id = :document_id AND l.pdf_page = :pdf_page AND l.text IS NOT NULL
  UNION ALL
  SELECT p.text, 2 AS preference, p.fetched_at AS read_at
  FROM strata.bronze.document_pages AS p
  WHERE p.document_id = :document_id AND p.pdf_page = :pdf_page
) AS readings
ORDER BY preference, read_at DESC
LIMIT 1
