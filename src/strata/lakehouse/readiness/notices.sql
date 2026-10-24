-- The notices source's data readiness measures, per country and for every country (subject all):
--   coverage_rows            notices held, of the notices the source reported for the same requests.
--                            Per country only for requests that held that country's notices alone.
--                            Every page bronze holds counts, as for every search source
--                            (strata.lakehouse.pages.reads_every_page).
--   coverage_years           fiscal years with notices, of the fiscal years from the first to the last
--   linked_project           notices whose project record is held, of all notices
--   contact_details_removed  notices that had contact names, addresses, emails, phone numbers or
--                            web addresses removed when they were fetched, of the notices held
--   awarded_bidder_id_on_award   awarded bidders of Contract Award notices whose STEP supplier ID is
--                            on the award rows of the same STEP reference, of the awarded bidders with
--                            an ID whose STEP reference has award rows (ticket 19)
--   awarded_bidder_id_same_name  of the awarded bidders with an ID named the same as a supplier on
--                            those award rows (in capitals, letters and digits only), those whose ID
--                            is the one the award rows give that name. docs/PLAN.md section 3 says
--                            the two IDs are equal; these two measures show how often they are.
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
),
awarded AS (
  SELECT
    l.country_code,
    b.step_supplier_id,
    upper(regexp_replace(b.name, '[^A-Za-z0-9]', '')) AS squashed_name,
    l.step_reference
  FROM latest AS l
  JOIN strata.silver.notice_bidders AS b ON b.notice_id = l.notice_id AND b.page_hash = l.page_hash
  WHERE b.step_supplier_id IS NOT NULL AND l.country_code IS NOT NULL
),
award_rows AS (
  SELECT DISTINCT step_reference, supplier_id, upper(regexp_replace(supplier, '[^A-Za-z0-9]', '')) AS squashed_name
  FROM strata.silver.awards_current
  WHERE step_reference IS NOT NULL AND supplier_id IS NOT NULL
),
compared AS (
  SELECT
    a.country_code,
    EXISTS (SELECT 1 FROM award_rows AS r WHERE r.step_reference = a.step_reference) AS on_award,
    EXISTS (SELECT 1 FROM award_rows AS r
            WHERE r.step_reference = a.step_reference AND r.supplier_id = a.step_supplier_id) AS same_id,
    EXISTS (SELECT 1 FROM award_rows AS r
            WHERE r.step_reference = a.step_reference AND r.squashed_name = a.squashed_name) AS same_name,
    EXISTS (SELECT 1 FROM award_rows AS r
            WHERE r.step_reference = a.step_reference AND r.squashed_name = a.squashed_name
              AND r.supplier_id = a.step_supplier_id) AS same_name_same_id
  FROM awarded AS a
),
supplier_ids AS (
  SELECT
    country_code AS subject,
    count(CASE WHEN on_award THEN 1 END) AS on_award,
    count(CASE WHEN same_id THEN 1 END) AS same_id,
    count(CASE WHEN same_name THEN 1 END) AS same_name,
    count(CASE WHEN same_name_same_id THEN 1 END) AS same_name_same_id
  FROM compared
  GROUP BY country_code
  UNION ALL
  SELECT
    'all',
    count(CASE WHEN on_award THEN 1 END),
    count(CASE WHEN same_id THEN 1 END),
    count(CASE WHEN same_name THEN 1 END),
    count(CASE WHEN same_name_same_id THEN 1 END)
  FROM compared
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
SELECT 'notices', subject, 'awarded_bidder_id_on_award', 'linked', CAST(same_id AS BIGINT), CAST(on_award AS BIGINT),
  CAST(NULL AS DATE),
  'This counts the awarded bidders whose STEP supplier ID is on the award rows of the same STEP reference, out of the awarded bidders with an ID whose STEP reference has award rows.'
FROM supplier_ids
WHERE on_award > 0
UNION ALL
SELECT 'notices', subject, 'awarded_bidder_id_same_name', 'linked', CAST(same_name_same_id AS BIGINT),
  CAST(same_name AS BIGINT), CAST(NULL AS DATE),
  'This counts the awarded bidders whose STEP supplier ID is the one the award rows give the same name on the same STEP reference, out of the awarded bidders with an ID named the same on those rows.'
FROM supplier_ids
WHERE same_name > 0
UNION ALL
SELECT 'notices', country_code, 'fresh_fetched', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
UNION ALL
SELECT 'notices', country_code, 'fresh_newest_record', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
