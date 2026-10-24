-- The IEG ratings dataset's ratings of one project (strata.gold.ieg_rating), one row per evaluation, each
-- rating word for word under the dataset's own field name. The dataset gives no date, so each row is public
-- from June 30 of its evaluation year (ticket 17).
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
WHERE r.project_id = :project_id
ORDER BY r.evaluation_fy, r.evaluation_type
