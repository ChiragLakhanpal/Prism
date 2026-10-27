-- project_signals: the monthly loan history (gold.project_closing_date) of every project whose ID sorts from :first
-- to :last, as history.sql reads one project's, as reported by the as-of date: its first month, then each month the
-- closing date changed (strata.tools.withheld.statuses_between, ticket 89). One statement for each batch of the
-- signals' replay, where history.sql reads one project.
SELECT
  project_id,
  closing_date,
  previous_closing_date,
  reported_on,
  public_from
FROM strata.gold.project_closing_date
WHERE project_id >= :first
  AND project_id <= :last
  AND public_from <= :as_of
ORDER BY project_id, reported_on
