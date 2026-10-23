-- strata.gold.ieg_rating: each IEG evaluation of a project from the newest page that held it.
-- key: project_id, evaluation_type, evaluation_fy
SELECT
  project_id,
  evaluation_type,
  evaluation_fiscal_year AS evaluation_fy,
  outcome,
  bank_performance,
  quality_at_entry,
  quality_of_supervision,
  me_quality,
  global_practice,
  public_from
FROM strata.silver.ieg_ratings
WHERE evaluation_type IS NOT NULL AND evaluation_fiscal_year IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY project_id, evaluation_type, evaluation_fiscal_year
                           ORDER BY fetched_at DESC, page_hash) = 1
