-- The IEG ratings dataset's ratings of the run's projects (strata.gold.ieg_rating), one row per evaluation, each
-- rating word for word under the dataset's own field name. The dataset gives no date, so each row is public
-- from June 30 of its evaluation year (ticket 17).
-- :every_project true reads every project at once (the nightly run, ticket 43); false reads the projects in
-- :projects, joined by commas, which no project id contains (one project's page).
SELECT
  r.project_id,
  r.evaluation_type,
  r.evaluation_fy,
  r.outcome,
  r.bank_performance,
  r.quality_at_entry,
  r.quality_of_supervision,
  r.me_quality,
  r.public_from
FROM strata.gold.ieg_rating AS r
WHERE (:every_project OR array_contains(split(:projects, ','), r.project_id))
ORDER BY r.evaluation_fy, r.evaluation_type
