-- The day the projects API was last fetched, for All projects' source line ("records through").
SELECT max(public_from) AS fetched_on
FROM strata.bronze.api_pages
WHERE source = :source
