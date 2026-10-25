-- One row for each try of each task of each run of the nightly job (docs/PLAN.md section 11). A task
-- writes its row when it finishes. A Databricks repair run keeps the run's id, so a task tried again has
-- a row for each try, and its last try is its outcome. Each task's quality checks are in
-- strata.ops.quality_checks (ticket 43).
--
-- run_id        the job run's id, or local-... for a run on this computer
-- task_key      the task, as bundle/nightly.yml names it
-- status        succeeded, or failed
-- rows_changed  rows the task added, changed or removed; 0 on a night that changed nothing, except the
--               rows a task adds to the run logs (strata.lakehouse.nightly.RUN_LOGS)
-- started_at    when the task started, in UTC
-- finished_at   when the task finished, in UTC
-- public_from   the day the task finished, in UTC: the day this row became known (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.pipeline_runs (
  run_id STRING NOT NULL,
  task_key STRING NOT NULL,
  status STRING NOT NULL,
  rows_changed BIGINT NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
