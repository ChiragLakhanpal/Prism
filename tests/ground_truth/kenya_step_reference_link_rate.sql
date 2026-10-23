-- The STEP-reference link rate that the nightly job's last run wrote to strata.ops equals a
-- direct count over gold: Kenya's contracts carrying a STEP reference, out of all its contracts.
-- It returns true or false rather than the counts, so it holds on the fixture and on the
-- workspace alike. Run it on the warehouse, after the job has ingested Kenya, with:
-- uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- expect: measure,matches
-- expect: linked_step_reference,true
WITH last_run AS (
  SELECT run_id
  FROM strata.ops.data_readiness
  WHERE source = 'awards' AND measure = 'linked_step_reference' AND country_code = 'KE'
  ORDER BY measured_at DESC
  LIMIT 1
),
stored AS (
  SELECT d.numerator, d.denominator
  FROM strata.ops.data_readiness AS d
  JOIN last_run AS r ON r.run_id = d.run_id
  WHERE d.source = 'awards' AND d.measure = 'linked_step_reference' AND d.country_code = 'KE'
),
counted AS (
  SELECT count(step_reference) AS numerator, count(*) AS denominator
  FROM strata.gold.contract
  WHERE country_code = 'KE'
)
SELECT
  'linked_step_reference' AS measure,
  s.numerator = c.numerator AND s.denominator = c.denominator AS matches
FROM stored AS s
CROSS JOIN counted AS c
