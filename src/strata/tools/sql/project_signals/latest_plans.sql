-- project_signals: each implementing agency's latest Procurement Plan public by the as-of date, by the
-- agency's name as its plans write it, newest first. The tool keeps those dated within [signals]
-- plan_months of the as-of date and checks each with check_plan.
SELECT
  v.document_id,
  v.implementing_agency,
  v.plan_date,
  v.public_from
FROM strata.silver.plan_versions AS v
WHERE v.project_id = :project_id
  AND v.implementing_agency IS NOT NULL
  AND v.public_from <= :as_of
  AND NOT EXISTS (
    SELECT 1 FROM strata.silver.plan_versions AS later
    WHERE later.project_id = v.project_id
      AND later.implementing_agency = v.implementing_agency
      AND later.public_from <= :as_of
      AND (later.plan_date > v.plan_date OR (later.plan_date = v.plan_date AND later.document_id > v.document_id))
  )
ORDER BY v.plan_date DESC, v.implementing_agency
