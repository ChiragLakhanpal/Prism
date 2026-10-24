-- The project page's header (the 10 brief, section 3): the project's name, country, status and
-- implementing agencies, from the newest record the projects API returned. The status and the
-- agencies change in place, so they count as public from the day that record was last updated
-- (ADR 0002); record_updated_on lets the route leave them out before then.
SELECT
  p.project_id,
  p.project_name,
  c.country_name AS country,
  p.status,
  p.implementing_agency,
  p.public_from,
  (SELECT max(s.last_updated_on) FROM strata.silver.projects AS s WHERE s.project_id = p.project_id)
    AS record_updated_on
FROM strata.gold.project AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
