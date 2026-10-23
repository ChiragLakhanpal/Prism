-- The awards source's data readiness measures, per country:
--   coverage_rows          award rows held, of the rows the source reported for the same requests
--   coverage_years         fiscal years with awards, of the fiscal years from the first to the last
--   linked_step_reference  contracts carrying a STEP reference, of all contracts
--   linked_notice          contracts whose STEP reference a notice also carries, of all contracts
--   linked_project         contracts whose project gold holds, of all contracts
--   fresh_fetched          the day of the last fetch, with the source's cadence
--   fresh_newest_record    the newest signing date fetched, with the source's cadence
WITH held AS (
  SELECT
    borrower_country_code AS country_code,
    count(*) AS award_rows,
    count(DISTINCT fiscal_year) AS years_held,
    max(fiscal_year) - min(fiscal_year) + 1 AS years_spanned
  FROM strata.silver.awards_current
  WHERE borrower_country_code IS NOT NULL
  GROUP BY borrower_country_code
),
pages AS (
  SELECT DISTINCT
    s.borrower_country_code AS country_code,
    regexp_replace(p.request, '&(top|skip)=[0-9]+', '') AS query,
    p.page_hash,
    p.reported_total,
    p.fetched_at,
    p.newest_record_on
  FROM strata.silver.awards AS s
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
),
linked AS (
  SELECT
    c.country_code,
    count(*) AS contracts,
    count(c.step_reference) AS with_reference,
    count(n.step_reference) AS with_notice,
    count(p.project_id) AS with_project
  FROM strata.gold.contract AS c
  LEFT JOIN (SELECT DISTINCT step_reference FROM strata.gold.notice) AS n ON n.step_reference = c.step_reference
  LEFT JOIN strata.gold.project AS p ON p.project_id = c.project_id
  WHERE c.country_code IS NOT NULL
  GROUP BY c.country_code
)
SELECT
  'awards' AS source,
  h.country_code AS subject,
  'coverage_rows' AS measure,
  'coverage' AS kind,
  CAST(h.award_rows AS BIGINT) AS count,
  CAST(r.total AS BIGINT) AS denominator,
  CAST(NULL AS DATE) AS as_of,
  'This counts the award rows held, out of the rows the source reported.' AS detail
FROM held AS h
LEFT JOIN reported AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'awards', country_code, 'coverage_years', 'coverage', CAST(years_held AS BIGINT), CAST(years_spanned AS BIGINT),
  CAST(NULL AS DATE), 'This counts the fiscal years that have awards, out of the fiscal years from the first to the last.'
FROM held
UNION ALL
SELECT 'awards', country_code, 'linked_step_reference', 'linked', CAST(with_reference AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts that carry a STEP reference, out of all contracts.'
FROM linked
UNION ALL
SELECT 'awards', country_code, 'linked_notice', 'linked', CAST(with_notice AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts whose STEP reference a notice also carries, out of all contracts.'
FROM linked
UNION ALL
SELECT 'awards', country_code, 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts whose project record is held, out of all contracts.'
FROM linked
UNION ALL
SELECT 'awards', country_code, 'fresh_fetched', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
UNION ALL
SELECT 'awards', country_code, 'fresh_newest_record', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
