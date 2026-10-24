-- One package with the criteria of its latest save, whoever made it: the caller applies the access rule.
-- Written without QUALIFY, so it runs on Lakebase's Postgres as on DuckDB (src/strata/appstate).
SELECT package_id, author_id, author_name, sentence, run_id, created_at,
       save_id, criteria, plan_months, plan_before_range, saved_at
FROM (
  SELECT p.package_id, p.author_id, p.author_name, p.sentence, p.run_id, p.created_at,
         s.save_id, s.criteria, s.plan_months, s.plan_before_range, s.saved_at,
         row_number() OVER (PARTITION BY s.package_id ORDER BY s.saved_at DESC, s.save_id DESC) AS newest
  FROM strata.app.planned_packages AS p
  JOIN strata.app.planned_package_saves AS s ON s.package_id = p.package_id
  WHERE p.package_id = :package_id
) AS saved
WHERE newest = 1
