-- The FY2001 to FY2016 awards' data readiness measures, for every country (subject all):
--   coverage_years   fiscal years with contracts, of the fiscal years from the first to the last
--   linked_project   contracts whose project record is held, of all its contracts
--   linked_country   contracts whose country Prism knows by its code, of all its contracts: the
--                    dataset names a country only in words
-- Its coverage_rows and freshness are written for every source at once (strata.lakehouse.readiness).
WITH contracts AS (
  SELECT c.fiscal_year, c.country_code, p.project_id AS held_project
  FROM strata.gold.contract AS c
  LEFT JOIN strata.gold.project AS p ON p.project_id = c.project_id
  WHERE c.source = 'awards_fy2001_2016'
),
held AS (
  SELECT
    count(*) AS contracts,
    count(held_project) AS with_project,
    count(country_code) AS with_country,
    count(DISTINCT fiscal_year) AS years_held,
    max(fiscal_year) - min(fiscal_year) + 1 AS years_spanned
  FROM contracts
)
SELECT 'awards_fy2001_2016' AS source, 'all' AS subject, 'coverage_years' AS measure, 'coverage' AS kind,
  CAST(years_held AS BIGINT) AS count, CAST(years_spanned AS BIGINT) AS denominator, CAST(NULL AS DATE) AS as_of,
  'This counts the fiscal years that have contracts, out of the fiscal years from the first to the last.' AS detail
FROM held
WHERE contracts > 0
UNION ALL
SELECT 'awards_fy2001_2016', 'all', 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts whose project record is held, out of all contracts.'
FROM held
WHERE contracts > 0
UNION ALL
SELECT 'awards_fy2001_2016', 'all', 'linked_country', 'linked', CAST(with_country AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts whose country is known by its code, out of all contracts.'
FROM held
WHERE contracts > 0
