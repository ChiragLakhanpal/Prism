-- The notices source's data readiness measures, per country:
--   coverage_rows            notices held, of the notices the source reported for the same requests
--   coverage_years           fiscal years with notices, of the fiscal years from the first to the last
--   linked_project           notices whose project record is held, of all notices
--   contact_details_removed  contact names, emails and phone numbers removed when the pages were
--                            fetched, out of the notices held
--   fresh_fetched            the day of the last fetch, with the source's cadence
--   fresh_newest_record      the newest notice fetched, with the source's cadence
-- Notices name their country in words, which gold.country turns into its code.
WITH latest AS (
  SELECT n.*, c.country_code
  FROM strata.silver.notices AS n
  JOIN strata.gold.country AS c ON c.country_name = n.project_country
  QUALIFY row_number() OVER (PARTITION BY n.notice_id ORDER BY n.fetched_at DESC, n.page_hash) = 1
),
held AS (
  SELECT
    l.country_code,
    count(*) AS notices,
    count(p.project_id) AS with_project,
    count(DISTINCT CASE WHEN month(l.notice_date) >= 7 THEN year(l.notice_date) + 1 ELSE year(l.notice_date) END) AS years_held,
    max(CASE WHEN month(l.notice_date) >= 7 THEN year(l.notice_date) + 1 ELSE year(l.notice_date) END)
      - min(CASE WHEN month(l.notice_date) >= 7 THEN year(l.notice_date) + 1 ELSE year(l.notice_date) END) + 1
      AS years_spanned
  FROM latest AS l
  LEFT JOIN strata.gold.project AS p ON p.project_id = l.project_id
  GROUP BY l.country_code
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
reported AS (
  SELECT country_code, sum(total) AS total
  FROM (
    SELECT country_code, query, max_by(reported_total, fetched_at) AS total
    FROM pages
    GROUP BY country_code, query
  ) AS per_query
  GROUP BY country_code
),
removed AS (
  SELECT l.country_code, sum(p.contact_details_removed) AS removed
  FROM (SELECT DISTINCT country_code, page_hash FROM latest) AS l
  JOIN strata.bronze.api_pages AS p ON p.page_hash = l.page_hash
  GROUP BY l.country_code
),
fresh AS (
  SELECT country_code, CAST(max(fetched_at) AS DATE) AS fetched_on, max(newest_record_on) AS newest
  FROM pages
  GROUP BY country_code
)
SELECT
  'notices' AS source,
  h.country_code,
  'coverage_rows' AS measure,
  CAST(h.notices AS BIGINT) AS numerator,
  CAST(r.total AS BIGINT) AS denominator,
  CAST(NULL AS DATE) AS as_of,
  'Notices held, of the notices the source reported.' AS detail
FROM held AS h
LEFT JOIN reported AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'notices', country_code, 'coverage_years', CAST(years_held AS BIGINT), CAST(years_spanned AS BIGINT),
  CAST(NULL AS DATE), 'Fiscal years with notices, of the fiscal years from the first to the last.'
FROM held
UNION ALL
SELECT 'notices', country_code, 'linked_project', CAST(with_project AS BIGINT), CAST(notices AS BIGINT),
  CAST(NULL AS DATE), 'Notices whose project record is held.'
FROM held
UNION ALL
SELECT 'notices', h.country_code, 'contact_details_removed', CAST(r.removed AS BIGINT), CAST(h.notices AS BIGINT),
  CAST(NULL AS DATE), 'Contact names, emails and phone numbers removed from the notices held, before they were kept.'
FROM held AS h
JOIN removed AS r ON r.country_code = h.country_code
UNION ALL
SELECT 'notices', country_code, 'fresh_fetched', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
UNION ALL
SELECT 'notices', country_code, 'fresh_newest_record', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
