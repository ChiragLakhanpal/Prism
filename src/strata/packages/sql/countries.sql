-- The World Bank's country list, with each name exactly as the World Bank lists it, for the package workspace's
-- country chip. Read as the viewer.
SELECT country_code, country_name
FROM strata.gold.country
WHERE country_name IS NOT NULL
ORDER BY country_name, country_code
