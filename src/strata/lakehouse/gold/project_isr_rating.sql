-- strata.gold.project_isr_rating: each project's latest ISR ratings from the newest page the projects
-- API returned for it. The page's rows already hold each rating once (silver.project_isr_ratings);
-- two values for one rating on one date would both stay.
-- key: project_id, rating_code, isr_date, value
WITH newest AS (
  SELECT project_id, page_hash
  FROM strata.silver.projects
  QUALIFY row_number() OVER (PARTITION BY project_id ORDER BY fetched_at DESC, page_hash) = 1
)
SELECT DISTINCT
  r.project_id,
  r.rating_code,
  r.rating_name,
  r.isr_date,
  r.value,
  r.public_from
FROM strata.silver.project_isr_ratings AS r
JOIN newest AS n ON n.project_id = r.project_id AND n.page_hash = r.page_hash
