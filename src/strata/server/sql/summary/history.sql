-- A project's Summary: how its closing date moved, from the monthly loan history (gold.project_closing_date):
-- the first month of its history, then each month the closing date changed, as reported by the as-of date.
SELECT
  closing_date,
  previous_closing_date,
  reported_on,
  public_from
FROM strata.gold.project_closing_date
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY reported_on
