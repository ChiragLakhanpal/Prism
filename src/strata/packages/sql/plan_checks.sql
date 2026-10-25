-- The plan checks one person opened: each plan version once, at the last time they opened it, newest first.
-- Written without QUALIFY, so it runs on Lakebase's Postgres as on DuckDB (src/strata/appstate).
SELECT project_id, agency_id, implementing_agency, plan_date, latest, activities, opened_at
FROM (
  SELECT project_id, agency_id, implementing_agency, plan_date, latest, activities, opened_at,
         row_number() OVER (PARTITION BY project_id, agency_id, plan_date, latest ORDER BY opened_at DESC) AS newest
  FROM strata.app.plan_checks_opened
  WHERE viewer_id = :viewer_id
) AS opened
WHERE newest = 1
ORDER BY opened_at DESC, project_id, agency_id
