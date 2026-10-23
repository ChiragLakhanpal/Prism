-- FY2017 to FY2019, which neither awards dataset covers: the contracts gold built from award notices
-- in each fiscal year equal a direct count of Contract Award notices for that year, by the fiscal
-- year of the contract's signature date, or of the notice's date when it gives none. Each of them
-- is labeled as local currency from award notices. It returns true or false rather than the
-- counts, so it holds on the fixture and on the workspace alike; tests/ground_truth/values.toml's
-- [counts.gap_years] lists the fixture's notices by year. Run it on the warehouse, after the job
-- has run, with: uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- expect: fiscal_year,matches,labeled
-- expect: 2017,true,true
-- expect: 2018,true,true
-- expect: 2019,true,true
WITH years AS (
  SELECT fiscal_year
  FROM VALUES (2017), (2018), (2019) AS gap(fiscal_year)
),
notices AS (
  SELECT
    CASE
      WHEN month(coalesce(contract_signature_date, notice_date)) >= 7
        THEN year(coalesce(contract_signature_date, notice_date)) + 1
      ELSE year(coalesce(contract_signature_date, notice_date))
    END AS fiscal_year
  FROM strata.gold.notice
  WHERE notice_type = 'Contract Award'
),
counted AS (
  SELECT fiscal_year, count(*) AS award_notices
  FROM notices
  GROUP BY fiscal_year
),
built AS (
  SELECT
    fiscal_year,
    count(*) AS contracts,
    count(CASE WHEN amount_basis = 'local currency, from award notices' THEN 1 END) AS labeled
  FROM strata.gold.contract
  WHERE source = 'notices'
  GROUP BY fiscal_year
)
SELECT
  y.fiscal_year,
  coalesce(b.contracts, 0) = coalesce(c.award_notices, 0) AS matches,
  coalesce(b.labeled, 0) = coalesce(b.contracts, 0) AS labeled
FROM years AS y
LEFT JOIN built AS b ON b.fiscal_year = y.fiscal_year
LEFT JOIN counted AS c ON c.fiscal_year = y.fiscal_year
ORDER BY y.fiscal_year
