-- The measures that count what the Data readiness page's fixes would unlock (ticket 16) equal direct
-- counts over gold, for every country (subject all) and for Kenya, in the nightly job's last run:
--   projects_with_contracts_lacking_step_reference  projects with a contract from the awards since
--       FY2020 that carries no STEP reference, out of the projects with any such contract
--   gap_years_contracts_in_local_currency  contracts built from award notices for FY2017 to FY2019
--       whose amount is in local currency, out of every contract built from those notices
--   gap_years_projects_in_local_currency  the projects of those contracts in local currency, out of
--       the projects of every contract built from those notices
-- It returns true or false rather than the counts, so it holds on the fixture and on the workspace
-- alike. Run it on the warehouse, after the job has run, with:
-- uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- expect: subject,measure,matches
-- expect: KE,gap_years_contracts_in_local_currency,true
-- expect: KE,gap_years_projects_in_local_currency,true
-- expect: KE,projects_with_contracts_lacking_step_reference,true
-- expect: all,gap_years_contracts_in_local_currency,true
-- expect: all,gap_years_projects_in_local_currency,true
-- expect: all,projects_with_contracts_lacking_step_reference,true
WITH last_run AS (
  SELECT max_by(run_id, measured_at) AS run_id
  FROM strata.ops.data_readiness
  WHERE source = 'awards' AND measure = 'projects_with_contracts_lacking_step_reference'
),
stored AS (
  SELECT d.subject, d.measure, d.count, d.denominator
  FROM strata.ops.data_readiness AS d
  JOIN last_run AS r ON r.run_id = d.run_id
  WHERE d.source = 'awards' AND d.subject IN ('all', 'KE')
),
awarded AS (
  SELECT project_id, country_code, step_reference
  FROM strata.gold.contract
  WHERE source = 'awards' AND project_id IS NOT NULL
),
gap_years AS (
  SELECT project_id, country_code, amount_basis
  FROM strata.gold.contract
  WHERE source = 'notices' AND fiscal_year BETWEEN 2017 AND 2019
),
counted AS (
  SELECT 'all' AS subject, 'projects_with_contracts_lacking_step_reference' AS measure,
    count(DISTINCT CASE WHEN step_reference IS NULL THEN project_id END) AS count,
    count(DISTINCT project_id) AS denominator
  FROM awarded
  UNION ALL
  SELECT 'KE', 'projects_with_contracts_lacking_step_reference',
    count(DISTINCT CASE WHEN step_reference IS NULL THEN project_id END), count(DISTINCT project_id)
  FROM awarded
  WHERE country_code = 'KE'
  UNION ALL
  SELECT 'all', 'gap_years_contracts_in_local_currency',
    count(CASE WHEN amount_basis = 'local currency, from award notices' THEN 1 END), count(*)
  FROM gap_years
  UNION ALL
  SELECT 'KE', 'gap_years_contracts_in_local_currency',
    count(CASE WHEN amount_basis = 'local currency, from award notices' THEN 1 END), count(*)
  FROM gap_years
  WHERE country_code = 'KE'
  UNION ALL
  SELECT 'all', 'gap_years_projects_in_local_currency',
    count(DISTINCT CASE WHEN amount_basis = 'local currency, from award notices' THEN project_id END),
    count(DISTINCT project_id)
  FROM gap_years
  UNION ALL
  SELECT 'KE', 'gap_years_projects_in_local_currency',
    count(DISTINCT CASE WHEN amount_basis = 'local currency, from award notices' THEN project_id END),
    count(DISTINCT project_id)
  FROM gap_years
  WHERE country_code = 'KE'
)
SELECT
  c.subject,
  c.measure,
  coalesce(s.count = c.count AND s.denominator = c.denominator, false) AS matches
FROM counted AS c
LEFT JOIN stored AS s ON s.subject = c.subject AND s.measure = c.measure
ORDER BY c.subject, c.measure
