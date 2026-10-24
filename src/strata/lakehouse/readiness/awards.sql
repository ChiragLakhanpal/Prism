-- The awards source's data readiness measures, per country and for every country (subject all):
--   coverage_rows          award rows held, of the rows the source reported for the same requests.
--                          Per country only for requests that held that country's rows alone, as a
--                          request for every country reports no total per country.
--   coverage_years         fiscal years with awards, of the fiscal years from the first to the last
--   linked_step_reference  contracts carrying a STEP reference, of all contracts
--   linked_notice          contracts whose STEP reference a notice also carries, of all contracts
--   linked_project         contracts whose project gold holds, of all contracts
--   fresh_fetched          per country: the day of the last fetch, with the source's cadence
--   fresh_newest_record    per country: the newest signing date fetched, with the source's cadence
-- And what the Data readiness page's fixes would unlock (ticket 16; kind fix), per country and for
-- every country:
--   projects_with_contracts_lacking_step_reference  projects with a contract that carries no STEP
--                          reference, of the projects with any contract
--   gap_years_contracts_in_local_currency  contracts built from award notices for FY2017 to FY2019,
--                          which neither awards dataset covers, whose amount is in local currency, of
--                          every contract built from those notices
--   gap_years_projects_in_local_currency   the projects of those contracts in local currency, of the
--                          projects of every contract built from those notices
-- The measures for every country's coverage_rows and freshness are written for every source at
-- once (strata.lakehouse.readiness). Contracts here are the awards dataset's own (source awards).
WITH held AS (
  SELECT
    borrower_country_code AS country_code,
    count(DISTINCT fiscal_year) AS years_held,
    max(fiscal_year) - min(fiscal_year) + 1 AS years_spanned
  FROM strata.silver.awards_current
  WHERE borrower_country_code IS NOT NULL
  GROUP BY borrower_country_code
),
held_all AS (
  SELECT count(DISTINCT fiscal_year) AS years_held, max(fiscal_year) - min(fiscal_year) + 1 AS years_spanned
  FROM strata.silver.awards_current
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
one_country AS (
  SELECT query
  FROM pages
  GROUP BY query
  HAVING count(DISTINCT country_code) = 1
),
rows_held AS (
  SELECT s.borrower_country_code AS country_code, count(*) AS award_rows
  FROM strata.silver.awards_current AS s
  JOIN pages AS p ON p.page_hash = s.page_hash AND p.country_code = s.borrower_country_code
  JOIN one_country AS o ON o.query = p.query
  GROUP BY s.borrower_country_code
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
),
contracts AS (
  SELECT
    c.country_code,
    c.step_reference,
    n.step_reference AS noticed_reference,
    p.project_id AS held_project
  FROM strata.gold.contract AS c
  LEFT JOIN (SELECT DISTINCT step_reference FROM strata.gold.notice) AS n ON n.step_reference = c.step_reference
  LEFT JOIN strata.gold.project AS p ON p.project_id = c.project_id
  WHERE c.source = 'awards'
),
linked AS (
  SELECT
    country_code AS subject,
    count(*) AS contracts,
    count(step_reference) AS with_reference,
    count(noticed_reference) AS with_notice,
    count(held_project) AS with_project
  FROM contracts
  WHERE country_code IS NOT NULL
  GROUP BY country_code
  UNION ALL
  SELECT 'all', count(*), count(step_reference), count(noticed_reference), count(held_project)
  FROM contracts
),
projects_missing AS (
  SELECT country_code AS subject,
    count(DISTINCT CASE WHEN step_reference IS NULL THEN project_id END) AS lacking,
    count(DISTINCT project_id) AS projects
  FROM strata.gold.contract
  WHERE source = 'awards' AND project_id IS NOT NULL AND country_code IS NOT NULL
  GROUP BY country_code
  UNION ALL
  SELECT 'all', count(DISTINCT CASE WHEN step_reference IS NULL THEN project_id END), count(DISTINCT project_id)
  FROM strata.gold.contract
  WHERE source = 'awards' AND project_id IS NOT NULL
),
gap_year_contracts AS (
  SELECT project_id, country_code, amount_basis = 'local currency, from award notices' AS in_local_currency
  FROM strata.gold.contract
  WHERE source = 'notices' AND fiscal_year BETWEEN 2017 AND 2019
),
gap_years AS (
  SELECT country_code AS subject,
    count(CASE WHEN in_local_currency THEN 1 END) AS local_contracts,
    count(*) AS contracts,
    count(DISTINCT CASE WHEN in_local_currency THEN project_id END) AS local_projects,
    count(DISTINCT project_id) AS projects
  FROM gap_year_contracts
  WHERE country_code IS NOT NULL
  GROUP BY country_code
  UNION ALL
  SELECT 'all', count(CASE WHEN in_local_currency THEN 1 END), count(*),
    count(DISTINCT CASE WHEN in_local_currency THEN project_id END), count(DISTINCT project_id)
  FROM gap_year_contracts
),
years AS (
  SELECT country_code AS subject, years_held, years_spanned FROM held
  UNION ALL
  SELECT 'all', years_held, years_spanned FROM held_all WHERE years_held > 0
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
FROM rows_held AS h
JOIN reported AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'awards', subject, 'coverage_years', 'coverage', CAST(years_held AS BIGINT), CAST(years_spanned AS BIGINT),
  CAST(NULL AS DATE), 'This counts the fiscal years that have awards, out of the fiscal years from the first to the last.'
FROM years
UNION ALL
SELECT 'awards', subject, 'linked_step_reference', 'linked', CAST(with_reference AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts that carry a STEP reference, out of all contracts.'
FROM linked
WHERE contracts > 0
UNION ALL
SELECT 'awards', subject, 'linked_notice', 'linked', CAST(with_notice AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts whose STEP reference a notice also carries, out of all contracts.'
FROM linked
WHERE contracts > 0
UNION ALL
SELECT 'awards', subject, 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(contracts AS BIGINT),
  CAST(NULL AS DATE), 'This counts the contracts whose project record is held, out of all contracts.'
FROM linked
WHERE contracts > 0
UNION ALL
SELECT 'awards', country_code, 'fresh_fetched', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
WHERE country_code IS NOT NULL
UNION ALL
SELECT 'awards', country_code, 'fresh_newest_record', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
WHERE country_code IS NOT NULL
UNION ALL
SELECT 'awards', subject, 'projects_with_contracts_lacking_step_reference', 'fix', CAST(lacking AS BIGINT),
  CAST(projects AS BIGINT), CAST(NULL AS DATE),
  'This counts the projects with a contract that carries no STEP reference, out of the projects with any contract.'
FROM projects_missing
WHERE projects > 0
UNION ALL
SELECT 'awards', subject, 'gap_years_contracts_in_local_currency', 'fix', CAST(local_contracts AS BIGINT),
  CAST(contracts AS BIGINT), CAST(NULL AS DATE),
  'This counts the contracts built from award notices for FY2017 to FY2019 whose amount is in local currency, out of every contract built from those notices.'
FROM gap_years
WHERE contracts > 0
UNION ALL
SELECT 'awards', subject, 'gap_years_projects_in_local_currency', 'fix', CAST(local_projects AS BIGINT),
  CAST(projects AS BIGINT), CAST(NULL AS DATE),
  'This counts the projects of the contracts built from award notices for FY2017 to FY2019 whose amount is in local currency, out of the projects of every contract built from those notices.'
FROM gap_years
WHERE contracts > 0
