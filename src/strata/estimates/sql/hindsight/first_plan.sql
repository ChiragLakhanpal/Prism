-- The hindsight test (ticket 34): the packages of a project's first Procurement Plan, largest first. The first
-- plan is the project's earliest plan version Strata read, by plan date, of any implementing agency. Each row is
-- a package the replay asks the risk-table builder about, with what its criteria are read from: its section (the
-- procurement category), its Method and its project's country. The replay reads it as of the release, since the
-- packages are the question; the answer is frozen at the approval date.
WITH first_plan AS (
  SELECT v.document_id
  FROM strata.silver.plan_versions AS v
  WHERE v.project_id = :project_id
    AND v.public_from <= :as_of
  ORDER BY v.plan_date, v.series_order, v.document_id
  LIMIT 1
)
SELECT
  r.document_id,
  r.activity_reference_no,
  r.section,
  r.description,
  r.method,
  r.estimated_amount_usd,
  p.country_code,
  r.public_from
FROM strata.silver.plan_rows AS r
JOIN first_plan AS f ON f.document_id = r.document_id
LEFT JOIN strata.gold.project AS p ON p.project_id = r.project_id
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
ORDER BY r.estimated_amount_usd DESC NULLS LAST, r.activity_reference_no
