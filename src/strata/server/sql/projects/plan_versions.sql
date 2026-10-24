-- The Procurement tab (the 10 brief, section 3): every version of the project's Procurement Plans
-- public by the as-of date, newest first, with how many activities the plan reader found in each
-- version it read. A version whose tables the reader did not read has no parse_reason and no rows.
WITH counted AS (
  SELECT document_id, count(*) AS activities
  FROM strata.silver.plan_rows
  WHERE project_id = :project_id
    AND public_from <= :as_of
  GROUP BY document_id
)
SELECT
  v.document_id,
  v.implementing_agency,
  v.plan_date,
  v.disclosed_on,
  v.parse_reason,
  COALESCE(n.activities, 0) AS activities
FROM strata.silver.plan_versions AS v
LEFT JOIN counted AS n ON n.document_id = v.document_id
WHERE v.project_id = :project_id
  AND v.public_from <= :as_of
ORDER BY v.plan_date DESC, v.public_from DESC, v.document_id DESC
