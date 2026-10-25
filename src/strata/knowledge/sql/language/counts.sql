-- How many passages carry a language the language registry knows, out of every passage.
SELECT language, count(*) AS passages FROM strata.silver.passages GROUP BY language ORDER BY language
