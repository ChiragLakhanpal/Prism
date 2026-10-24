-- check_plan: the project and its closing date, from the newest record the projects API returned.
--
-- The projects API changes a closing date in place when a project is extended, and gold keeps only
-- the newest record. So the closing date counts as public from the day that record was last
-- updated (last_updated_on), not from the project's own public date: an as-of date before then
-- gets no closing date rather than a later one (ADR 0002). The implementing agencies the record
-- names follow the same rule; they name an agency that has published no plan yet.
SELECT
  p.project_id,
  p.project_name,
  p.status,
  p.closing_date,
  p.implementing_agency,
  p.public_from,
  (SELECT max(s.last_updated_on) FROM strata.silver.projects AS s WHERE s.project_id = p.project_id)
    AS record_updated_on
FROM strata.gold.project AS p
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
