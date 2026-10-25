-- estimate_time on an upload's row (ticket 38): the country of the upload's project, whose packages a row no record
-- holds is compared with.
SELECT p.country_code
FROM strata.gold.project AS p
WHERE p.project_id = :project_id
