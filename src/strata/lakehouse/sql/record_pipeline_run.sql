-- Records one finished task of the nightly job. The job runs it with spark.sql, and the gate runs it
-- on DuckDB through the transpile step, with the same named parameters.
INSERT INTO strata.ops.pipeline_runs
  (run_id, task_key, status, rows_changed, started_at, finished_at, public_from)
VALUES
  (:run_id, :task_key, :status, :rows_changed, :started_at, :finished_at, :public_from)
