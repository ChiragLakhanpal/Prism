-- The projects source's data readiness measures, per country and for every country (subject all):
--   coverage_rows        projects held, of the projects the source reported for the same requests.
--                        Per country only for requests that held that country's projects alone,
--                        and only from the newest page of each request (strata.bronze.current_pages),
--                        so a project the source no longer returns is not counted.
--   coverage_years       approval fiscal years with projects, of the fiscal years from the first to the last
--   linked_sector        projects mapped to one sector of Strata's taxonomy (config/sectors.toml), of
--                        all projects. A project is left out when its record lists no major sector, or
--                        a code the sector file does not map.
--   fresh_fetched        per country: the day of the last fetch, with the source's cadence
--   fresh_newest_record  per country: the newest project update fetched, with the source's cadence
-- The measures for every country's coverage_rows and freshness are written for every source at
-- once (strata.lakehouse.readiness).
WITH held AS (
  SELECT
    country_code AS subject,
    count(*) AS projects,
    count(sector) AS with_sector,
    count(DISTINCT approval_fiscal_year) AS years_held,
    max(approval_fiscal_year) - min(approval_fiscal_year) + 1 AS years_spanned
  FROM strata.gold.project
  WHERE country_code IS NOT NULL
  GROUP BY country_code
  UNION ALL
  SELECT
    'all',
    count(*),
    count(sector),
    count(DISTINCT approval_fiscal_year),
    max(approval_fiscal_year) - min(approval_fiscal_year) + 1
  FROM strata.gold.project
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
one_country AS (
  SELECT query
  FROM pages
  GROUP BY query
  HAVING count(DISTINCT country_code) = 1
),
rows_held AS (
  SELECT country_code, sum(projects) AS projects
  FROM (
    SELECT p.country_code, p.query, count(DISTINCT s.project_id) AS projects
    FROM strata.silver.projects AS s
    JOIN pages AS p ON p.page_hash = s.page_hash AND p.country_code = s.country_code
    JOIN strata.bronze.current_pages AS c ON c.page_hash = p.page_hash
    JOIN one_country AS o ON o.query = p.query
    GROUP BY p.country_code, p.query
  ) AS per_query
  GROUP BY country_code
),
reported AS (
  SELECT country_code, sum(total) AS total
  FROM (
    SELECT p.country_code, p.query, max_by(p.reported_total, p.fetched_at) AS total
    FROM pages AS p
    JOIN one_country AS o ON o.query = p.query
    GROUP BY p.country_code, p.query
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
  h.country_code AS subject,
  'coverage_rows' AS measure,
  'coverage' AS kind,
  CAST(h.projects AS BIGINT) AS count,
  CAST(r.total AS BIGINT) AS denominator,
  CAST(NULL AS DATE) AS as_of,
  'This counts the projects held, once in each request they came back in, out of the projects the source reported.' AS detail
FROM rows_held AS h
JOIN reported AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'projects', subject, 'coverage_years', 'coverage', CAST(years_held AS BIGINT), CAST(years_spanned AS BIGINT),
  CAST(NULL AS DATE), 'This counts the fiscal years in which projects were approved, out of the fiscal years from the first to the last.'
FROM held
WHERE projects > 0
UNION ALL
SELECT 'projects', subject, 'linked_sector', 'linked', CAST(with_sector AS BIGINT), CAST(projects AS BIGINT),
  CAST(NULL AS DATE), 'This counts the projects mapped to one sector, out of all projects held.'
FROM held
WHERE projects > 0
UNION ALL
SELECT 'projects', country_code, 'fresh_fetched', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
UNION ALL
SELECT 'projects', country_code, 'fresh_newest_record', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
