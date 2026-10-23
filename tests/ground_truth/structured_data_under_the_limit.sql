-- Structured data in strata stays under 0.5 GB (docs/PLAN.md section 3; config/thresholds.toml,
-- ingestion.structured_data_limit_bytes): the bytes the nightly job's last run recorded for every
-- table but the documents' text and layout. It returns true or false rather than the bytes, so it
-- holds on the fixture and on the workspace alike. Run it on the warehouse, after the job has run
-- for every country, with: uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- param: limit_bytes = 500000000
-- expect: measured,under_the_limit
-- expect: true,true
WITH last_run AS (
  SELECT run_id
  FROM strata.ops.table_sizes
  ORDER BY measured_at DESC
  LIMIT 1
)
SELECT
  count(*) > 0 AS measured,
  coalesce(sum(CASE WHEN s.structured THEN s.bytes END), 0) < CAST(:limit_bytes AS BIGINT) AS under_the_limit
FROM strata.ops.table_sizes AS s
JOIN last_run AS r ON r.run_id = s.run_id
