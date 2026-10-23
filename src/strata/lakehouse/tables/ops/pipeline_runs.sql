-- One row for each task of each run of the nightly job (docs/PLAN.md section 11). A task writes
-- its row when it finishes. Ticket 43 adds the quality checks for the Governance page.
--
-- run_id        the job run's id, or local-... for a run on this computer
-- task_key      the task, as bundle/nightly.yml names it
-- status        succeeded, or failed
-- rows_changed  rows the task added, changed or removed; 0 for a task that does nothing yet
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
