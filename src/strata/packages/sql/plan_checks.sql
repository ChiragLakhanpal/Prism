-- The plan checks one person opened: each plan version once, at the last time they opened it, newest first.
SELECT project_id, agency_id, implementing_agency, plan_date, latest, activities, opened_at
FROM strata.ops.plan_checks_opened
WHERE viewer_id = :viewer_id
QUALIFY row_number() OVER (PARTITION BY project_id, agency_id, plan_date, latest ORDER BY opened_at DESC) = 1
ORDER BY opened_at DESC, project_id, agency_id
