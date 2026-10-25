-- A project's Summary (the 21 brief, section 3): the projects API's newest record of the project, with
-- the day it was last updated, since its status, closing date, region and agencies change in place and
-- count as public from that day (ADR 0002; check_plan's record_is_current).
SELECT
  p.project_id,
  p.project_name,
  c.country_name AS country,
  p.region,
  p.status,
  p.approval_date,
  p.closing_date,
  p.implementing_agency,
  p.sector_name,
  p.total_commitment_usd,
  p.public_from,
  (SELECT max(s.last_updated_on) FROM strata.silver.projects AS s WHERE s.project_id = p.project_id)
    AS record_updated_on
FROM strata.gold.project AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
