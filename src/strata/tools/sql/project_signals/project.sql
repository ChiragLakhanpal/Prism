-- Change projects_between.sql with this file. strata.tools.withheld.statuses_between reads the same
-- columns for the replay of the signals.
-- project_signals: the project, from the projects API's newest record, with its country's name and the
-- day the record was last updated. The API changes a status and a closing date in place, so they count as
-- public from that day (check_plan's record_is_current); before it, the closing date comes from the loan
-- history (history.sql).
SELECT
  p.project_id,
  p.project_name,
  c.country_name AS country,
  p.status,
  p.closing_date,
  p.implementing_agency,
  p.public_from,
  (SELECT max(s.last_updated_on) FROM strata.silver.projects AS s WHERE s.project_id = p.project_id)
    AS record_updated_on
FROM strata.gold.project AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
