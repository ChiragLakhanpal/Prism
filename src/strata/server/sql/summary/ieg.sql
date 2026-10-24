-- A project's Summary: IEG's ratings of the project, one row per evaluation, public by the as-of date.
SELECT
  evaluation_type,
  evaluation_fy,
  outcome,
  bank_performance,
  public_from
FROM strata.gold.ieg_rating
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY evaluation_fy DESC, evaluation_type
