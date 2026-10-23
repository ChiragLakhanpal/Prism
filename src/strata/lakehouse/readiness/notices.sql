-- The notices source's data readiness measures, per country and for every country (subject all):
--   coverage_rows            notices held, of the notices the source reported for the same requests.
--                            Per country only for requests that held that country's notices alone,
--                            and only from the newest page of each request (strata.bronze.current_pages),
--                            so a notice the source has withdrawn since is not counted.
--   coverage_years           fiscal years with notices, of the fiscal years from the first to the last
--   linked_project           notices whose project record is held, of all notices
--   contact_details_removed  notices that had contact names, addresses, emails, phone numbers or
--                            web addresses removed when they were fetched, of the notices held
--   fresh_fetched            per country: the day of the last fetch, with the source's cadence
--   fresh_newest_record      per country: the newest notice fetched, with the source's cadence
-- Notices name their country in words, which gold.country turns into its code. The measures for
-- every country's coverage_rows and freshness are written for every source at once
-- (strata.lakehouse.readiness).
WITH latest AS (
  SELECT n.*, c.country_code
  FROM strata.silver.notices AS n
  LEFT JOIN strata.gold.country AS c ON c.country_name = n.project_country
  QUALIFY row_number() OVER (PARTITION BY n.notice_id ORDER BY n.fetched_at DESC, n.page_hash) = 1
),
counted AS (
  SELECT
    l.country_code,
    l.fiscal_year,
    l.contact_details_removed,
    p.project_id AS held_project
  FROM latest AS l
  LEFT JOIN strata.gold.project AS p ON p.project_id = l.project_id
),
held AS (
  SELECT
    country_code AS subject,
    count(*) AS notices,
    count(held_project) AS with_project,
    count(CASE WHEN contact_details_removed THEN 1 END) AS with_contacts_removed,
    count(DISTINCT fiscal_year) AS years_held,
    max(fiscal_year) - min(fiscal_year) + 1 AS years_spanned
  FROM counted
  WHERE country_code IS NOT NULL
  GROUP BY country_code
  UNION ALL
  SELECT
    'all',
    count(*),
    count(held_project),
    count(CASE WHEN contact_details_removed THEN 1 END),
    count(DISTINCT fiscal_year),
    max(fiscal_year) - min(fiscal_year) + 1
  FROM counted
),
pages AS (
  SELECT DISTINCT
    c.country_code,
    regexp_replace(p.request, '&(rows|os)=[0-9]+', '') AS query,
    p.page_hash,
    p.reported_total,
    p.fetched_at,
    p.newest_record_on
  FROM strata.silver.notices AS s
  JOIN strata.gold.country AS c ON c.country_name = s.project_country
  JOIN strata.bronze.api_pages AS p ON p.page_hash = s.page_hash
),
one_country AS (
  SELECT query
  FROM pages
  GROUP BY query
  HAVING count(DISTINCT country_code) = 1
),
rows_held AS (
  SELECT p.country_code, count(DISTINCT l.notice_id) AS notices
  FROM latest AS l
  JOIN strata.silver.notices AS s ON s.notice_id = l.notice_id
  JOIN pages AS p ON p.page_hash = s.page_hash AND p.country_code = l.country_code
  JOIN strata.bronze.current_pages AS c ON c.page_hash = p.page_hash
  JOIN one_country AS o ON o.query = p.query
  GROUP BY p.country_code
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
  'notices' AS source,
  h.country_code AS subject,
  'coverage_rows' AS measure,
  'coverage' AS kind,
  CAST(h.notices AS BIGINT) AS count,
  CAST(r.total AS BIGINT) AS denominator,
  CAST(NULL AS DATE) AS as_of,
  'This counts the notices held, out of the notices the source reported.' AS detail
FROM rows_held AS h
JOIN reported AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'notices', subject, 'coverage_years', 'coverage', CAST(years_held AS BIGINT), CAST(years_spanned AS BIGINT),
  CAST(NULL AS DATE), 'This counts the fiscal years that have notices, out of the fiscal years from the first to the last.'
FROM held
WHERE notices > 0
UNION ALL
SELECT 'notices', subject, 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(notices AS BIGINT),
  CAST(NULL AS DATE), 'This counts the notices whose project record is held, out of all notices held.'
FROM held
WHERE notices > 0
UNION ALL
SELECT 'notices', subject, 'contact_details_removed', 'stripped', CAST(with_contacts_removed AS BIGINT),
  CAST(notices AS BIGINT), CAST(NULL AS DATE),
  'This counts the notices that had contact names, addresses, emails, phone numbers or web addresses removed before they were kept, out of the notices held.'
FROM held
WHERE notices > 0
UNION ALL
SELECT 'notices', country_code, 'fresh_fetched', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
UNION ALL
SELECT 'notices', country_code, 'fresh_newest_record', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
