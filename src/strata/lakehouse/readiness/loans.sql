-- The latest loan and credit snapshots' data readiness measures, for every country (subject all).
-- The IDA credits and the IBRD loans share this file; :source is the one being measured.
--   coverage_years   approval fiscal years with loans, of the fiscal years from the first to the last
--   linked_project   loans whose project record is held, of all its loans
-- Its coverage_rows and freshness are written for every source at once (strata.lakehouse.readiness).
WITH mine AS (
  SELECT DISTINCT s.loan_number
  FROM strata.silver.loans AS s
  JOIN strata.bronze.api_pages AS b ON b.page_hash = s.page_hash AND b.source = :source
),
loans AS (
  SELECT
    l.loan_number,
    p.project_id AS held_project,
    l.approval_fiscal_year AS fiscal_year
  FROM strata.gold.loan AS l
  JOIN mine AS m ON m.loan_number = l.loan_number
  LEFT JOIN strata.gold.project AS p ON p.project_id = l.project_id
),
held AS (
  SELECT
    count(*) AS loans,
    count(held_project) AS with_project,
    count(DISTINCT fiscal_year) AS years_held,
    max(fiscal_year) - min(fiscal_year) + 1 AS years_spanned
  FROM loans
)
SELECT :source AS source, 'all' AS subject, 'coverage_years' AS measure, 'coverage' AS kind,
  CAST(years_held AS BIGINT) AS count, CAST(years_spanned AS BIGINT) AS denominator, CAST(NULL AS DATE) AS as_of,
  'This counts the fiscal years in which loans were approved, out of the fiscal years from the first to the last.' AS detail
FROM held
WHERE loans > 0
UNION ALL
SELECT :source, 'all', 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(loans AS BIGINT),
  CAST(NULL AS DATE), 'This counts the loans whose project record is held, out of all loans.'
FROM held
WHERE loans > 0
