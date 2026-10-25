-- The country of one project a viewer checked a plan of, for the Packages tab's Country column. Read as the
-- viewer; the country's name comes from the World Bank's country list the workspace already read.
SELECT country_code
FROM strata.gold.project
WHERE project_id = :project_id
