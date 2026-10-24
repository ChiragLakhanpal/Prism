-- All projects (the 10 brief, section 4): every project Strata holds a record for, public by the
-- as-of date, active projects first and then by name, A to Z. The route sorts; the browser does not.
--
-- The projects API changes a status in place, and gold keeps only the newest record, so a status
-- counts as public from the day that record was last updated, as check_plan's project.sql reads the
-- closing date (ADR 0002). Before then the status is left empty rather than a later one.
-- record_current is that rule, written once here; strata.tools.check_plan.record_is_current is the
-- same rule for the project page and check_plan, which read one record at a time.
WITH records AS (
  SELECT project_id, max(last_updated_on) AS record_updated_on
  FROM strata.silver.projects
  GROUP BY project_id
),
listed AS (
  SELECT
    p.project_id,
    p.project_name,
    p.country_code,
    p.status,
    COALESCE(r.record_updated_on, p.public_from) <= :as_of AS record_current
  FROM strata.gold.project AS p
  LEFT JOIN records AS r ON r.project_id = p.project_id
  WHERE p.public_from <= :as_of
)
SELECT
  p.project_id,
  p.project_name,
  c.country_name AS country,
  CASE WHEN p.record_current THEN p.status END AS status
FROM listed AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
ORDER BY
  CASE WHEN p.record_current AND p.status = 'Active' THEN 0 ELSE 1 END,
  p.project_name,
  p.project_id
