-- Change histories_between.sql with this file. strata.tools.withheld.statuses_between reads the same
-- columns for the replay of the signals.
-- project_signals: how the project's closing date moved, from the monthly loan history
-- (gold.project_closing_date): its first month, then each month the closing date changed, as reported by
-- the as-of date. One row per project and month, so two credits that move together count once.
SELECT
  closing_date,
  previous_closing_date,
  reported_on,
  public_from
FROM strata.gold.project_closing_date
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY reported_on
