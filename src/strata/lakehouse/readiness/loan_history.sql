-- The monthly loan history's data readiness measures, for the slice's countries (subject all). The
-- IDA and IBRD histories share this file; :source is the one being measured.
--   coverage_years   fiscal years with a month of history, of the fiscal years from the first to the last
--   linked_project   loans in the history whose project record is held, of all its loans
-- Its coverage_rows and freshness are written for every source at once (strata.lakehouse.readiness).
WITH months AS (
  SELECT DISTINCT
    s.loan_number,
    s.project_id,
    CASE WHEN month(s.end_of_period) >= 7 THEN year(s.end_of_period) + 1 ELSE year(s.end_of_period) END AS fiscal_year
  FROM strata.silver.loan_history AS s
  JOIN strata.bronze.api_pages AS b ON b.page_hash = s.page_hash AND b.source = :source
),
loans AS (
  SELECT m.loan_number, max(p.project_id) AS held_project
  FROM months AS m
  LEFT JOIN strata.gold.project AS p ON p.project_id = m.project_id
  GROUP BY m.loan_number
),
held AS (
  SELECT
    (SELECT count(*) FROM loans) AS loans,
    (SELECT count(held_project) FROM loans) AS with_project,
    (SELECT count(DISTINCT fiscal_year) FROM months) AS years_held,
    (SELECT max(fiscal_year) - min(fiscal_year) + 1 FROM months) AS years_spanned
)
SELECT :source AS source, 'all' AS subject, 'coverage_years' AS measure, 'coverage' AS kind,
  CAST(years_held AS BIGINT) AS count, CAST(years_spanned AS BIGINT) AS denominator, CAST(NULL AS DATE) AS as_of,
  'This counts the fiscal years that have a month of history, out of the fiscal years from the first to the last.' AS detail
FROM held
WHERE loans > 0
UNION ALL
SELECT :source, 'all', 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(loans AS BIGINT),
  CAST(NULL AS DATE), 'This counts the loans in the history whose project record is held, out of all its loans.'
FROM held
WHERE loans > 0
