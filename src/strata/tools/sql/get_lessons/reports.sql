-- get_lessons: the completion reports of the projects of the comparable packages a call names, as of a date
-- (ticket 30). Each project of the packages (strata.gold.package, public on or before the as-of date) comes
-- with its newest ICR public by then that no re-issue had replaced, its key in the source view's address, and
-- how many of that ICR's passages Prism read by then. A project with no such ICR comes back with an empty
-- document_id. :packages holds the STEP references, joined by commas; :icr is the documents API's type for an
-- ICR.
WITH projects AS (
  SELECT DISTINCT p.project_id
  FROM strata.gold.package AS p
  WHERE array_contains(split(:packages, ','), p.step_reference)
    AND p.public_from <= :as_of
),
reports AS (
  SELECT d.project_id, d.document_id, d.version, d.document_type, d.document_date, d.doc_key, d.public_from
  FROM strata.silver.documents AS d
  WHERE d.document_type = :icr
    AND d.public_from <= :as_of
    AND (d.replaced_on IS NULL OR d.replaced_on > :as_of)
  QUALIFY row_number() OVER (PARTITION BY d.project_id ORDER BY d.document_date DESC, d.version DESC) = 1
)
SELECT
  pr.project_id,
  g.project_name,
  r.document_id,
  r.version,
  r.document_type,
  r.document_date,
  r.doc_key,
  r.public_from,
  (SELECT count(*)
   FROM strata.gold.passage AS s
   WHERE s.document_id = r.document_id
     AND s.version = r.version
     AND s.public_from <= :as_of) AS passages
FROM projects AS pr
LEFT JOIN strata.gold.project AS g ON g.project_id = pr.project_id
LEFT JOIN reports AS r ON r.project_id = pr.project_id
ORDER BY pr.project_id
