-- project_signals: every project whose ID sorts from :first to :last, with the columns of project.sql that the rule
-- for whether a project was active on the as-of date reads (strata.tools.withheld.statuses_between, ticket 89). The
-- signals' replay reads a date's projects this way in batches, one statement for each batch, where project.sql
-- reads one project. The record's update day comes from strata.silver.projects, as in project.sql.
SELECT
  p.project_id,
  p.status,
  p.closing_date,
  p.public_from,
  s.record_updated_on
FROM strata.gold.project AS p
LEFT JOIN (
  SELECT project_id, max(last_updated_on) AS record_updated_on
  FROM strata.silver.projects
  GROUP BY project_id
) AS s ON s.project_id = p.project_id
WHERE p.project_id >= :first
  AND p.project_id <= :last
  AND p.public_from <= :as_of
ORDER BY p.project_id
