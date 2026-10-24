-- The Procurement Plan pages the layout parser (Route B) tried and could not read, as of the date,
-- leaving out a page it read on a later try (strata.bronze.layout_pages). A page tried twice counts
-- once, on the day it last failed.
SELECT
  f.project_id,
  f.document_id,
  f.pdf_page,
  CAST(max(f.failed_at) AS DATE) AS failed_on,
  max(f.public_from) AS public_from
FROM strata.ops.parse_failures AS f
WHERE f.public_from <= :as_of
  AND NOT EXISTS (
    SELECT 1
    FROM strata.bronze.layout_pages AS l
    WHERE l.document_id = f.document_id AND l.pdf_page = f.pdf_page AND l.public_from <= :as_of
  )
GROUP BY f.project_id, f.document_id, f.pdf_page
ORDER BY f.project_id, f.document_id, f.pdf_page
