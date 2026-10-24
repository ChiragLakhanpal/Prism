-- The governance indicators' data readiness measures, for every country (subject all). CPIA and
-- WGI share this file; :source is the one being measured.
--   coverage_years   years with a score, of the years from the first to the last
--   linked_country   countries with a score that Strata holds as a borrowing country, of all the
--                    countries and groups with a score: the API also scores regions and income groups
-- Its coverage_rows and freshness are written for every source at once (strata.lakehouse.readiness).
WITH scored AS (
  SELECT DISTINCT s.country_code, s.year
  FROM strata.silver.indicators AS s
  JOIN strata.bronze.api_pages AS b ON b.page_hash = s.page_hash AND b.source = :source
  WHERE s.value IS NOT NULL
),
countries AS (
  SELECT DISTINCT s.country_code, c.country_code AS held_country
  FROM scored AS s
  LEFT JOIN strata.gold.country AS c ON c.country_code = s.country_code
),
held AS (
  SELECT
    (SELECT count(*) FROM countries) AS countries,
    (SELECT count(held_country) FROM countries) AS with_country,
    (SELECT count(DISTINCT year) FROM scored) AS years_held,
    (SELECT max(year) - min(year) + 1 FROM scored) AS years_spanned
)
SELECT :source AS source, 'all' AS subject, 'coverage_years' AS measure, 'coverage' AS kind,
  CAST(years_held AS BIGINT) AS count, CAST(years_spanned AS BIGINT) AS denominator, CAST(NULL AS DATE) AS as_of,
  'This counts the years that have a score, out of the years from the first to the last.' AS detail
FROM held
WHERE countries > 0
UNION ALL
SELECT :source, 'all', 'linked_country', 'linked', CAST(with_country AS BIGINT), CAST(countries AS BIGINT),
  CAST(NULL AS DATE), 'This counts the countries with a score that are held as borrowing countries, out of all with a score.'
FROM held
WHERE countries > 0
