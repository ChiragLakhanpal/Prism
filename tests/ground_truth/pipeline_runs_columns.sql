-- The second sample query for both engines. It lists the columns of strata.ops.pipeline_runs, so it
-- checks that the deploy and the fixture build made the same table from one definition. Run it on
-- the warehouse with:
-- uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
--
-- The expected rows are the seven columns in src/strata/lakehouse/tables/ops/pipeline_runs.sql,
-- in its order. It reads system.information_schema because DuckDB has no information_schema
-- inside an attached catalog. It does not return ordinal_position, which Databricks counts from 0
-- and DuckDB from 1.
-- expect: column_name
-- expect: run_id
-- expect: task_key
-- expect: status
-- expect: rows_changed
-- expect: started_at
-- expect: finished_at
-- expect: public_from
SELECT column_name
FROM system.information_schema.columns
WHERE table_catalog = 'strata'
  AND table_schema = 'ops'
  AND table_name = 'pipeline_runs'
ORDER BY ordinal_position
