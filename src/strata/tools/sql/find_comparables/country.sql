-- find_comparables: the name of the country a call compares within, as the World Bank lists it.
SELECT country_name
FROM strata.gold.country
WHERE country_code = :country
