-- The projects source's data readiness measures, per country:
--   coverage_rows        projects held, of the projects the source reported for the same requests
--   coverage_years       approval fiscal years with projects, of the fiscal years from the first to the last
--   fresh_fetched        the day of the last fetch, with the source's cadence
--   fresh_newest_record  the newest project update fetched, with the source's cadence
WITH held AS (
  SELECT
    country_code,
    count(*) AS projects,
    count(DISTINCT approval_fiscal_year) AS years_held,
    max(approval_fiscal_year) - min(approval_fiscal_year) + 1 AS years_spanned
  FROM strata.gold.project
  WHERE country_code IS NOT NULL
  GROUP BY country_code
),
pages AS (
  SELECT DISTINCT
    s.country_code,
    regexp_replace(p.request, '&(rows|os)=[0-9]+', '') AS query,
    p.page_hash,
    p.reported_total,
    p.fetched_at,
    p.newest_record_on
  FROM strata.silver.projects AS s
  JOIN strata.bronze.api_pages AS p ON p.page_hash = s.page_hash
),
reported AS (
  SELECT country_code, sum(total) AS total
  FROM (
    SELECT country_code, query, max_by(reported_total, fetched_at) AS total
    FROM pages
    GROUP BY country_code, query
  ) AS per_query
  GROUP BY country_code
),
fresh AS (
  SELECT country_code, CAST(max(fetched_at) AS DATE) AS fetched_on, max(newest_record_on) AS newest
  FROM pages
  GROUP BY country_code
)
SELECT
  'projects' AS source,
  h.country_code,
  'coverage_rows' AS measure,
  CAST(h.projects AS BIGINT) AS numerator,
  CAST(r.total AS BIGINT) AS denominator,
  CAST(NULL AS DATE) AS as_of,
  'Projects held, of the projects the source reported.' AS detail
FROM held AS h
LEFT JOIN reported AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'projects', country_code, 'coverage_years', CAST(years_held AS BIGINT), CAST(years_spanned AS BIGINT),
  CAST(NULL AS DATE), 'Approval fiscal years with projects, of the fiscal years from the first to the last.'
FROM held
UNION ALL
SELECT 'projects', country_code, 'fresh_fetched', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
UNION ALL
SELECT 'projects', country_code, 'fresh_newest_record', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
