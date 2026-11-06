-- The hindsight test (ticket 34): for each project named, its approval date, country and sector, its newest ICR
-- that no re-issue had replaced by :as_of, with how many of its passages Prism read, and its newest ICR Review
-- that no re-issue had replaced (a re-issue replaces the earlier version, as the evidence ladder says). A project
-- with no such report comes back with an empty document id. :projects holds the project IDs, joined by commas;
-- :icr and :icr_review are the documents API's types.
WITH icr AS (
  SELECT d.project_id, d.document_id, d.version
  FROM strata.silver.documents AS d
  WHERE array_contains(split(:projects, ','), d.project_id)
    AND d.document_type = :icr
    AND d.public_from <= :as_of
    AND (d.replaced_on IS NULL OR d.replaced_on > :as_of)
  QUALIFY row_number() OVER (PARTITION BY d.project_id ORDER BY d.document_date DESC, d.version DESC) = 1
),
review AS (
  SELECT d.project_id, d.document_id, d.version
  FROM strata.silver.documents AS d
  WHERE array_contains(split(:projects, ','), d.project_id)
    AND d.document_type = :icr_review
    AND d.public_from <= :as_of
    AND (d.replaced_on IS NULL OR d.replaced_on > :as_of)
  QUALIFY row_number() OVER (PARTITION BY d.project_id ORDER BY d.document_date DESC, d.version DESC) = 1
)
SELECT
  p.project_id,
  p.approval_date,
  p.country_code,
  p.sector,
  i.document_id AS icr_document_id,
  i.version AS icr_version,
  (SELECT count(*)
   FROM strata.gold.passage AS s
   WHERE s.document_id = i.document_id
     AND s.version = i.version) AS icr_passages,
  r.document_id AS review_document_id,
  r.version AS review_version,
  p.public_from
FROM strata.gold.project AS p
LEFT JOIN icr AS i ON i.project_id = p.project_id
LEFT JOIN review AS r ON r.project_id = p.project_id
WHERE array_contains(split(:projects, ','), p.project_id)
ORDER BY p.project_id
