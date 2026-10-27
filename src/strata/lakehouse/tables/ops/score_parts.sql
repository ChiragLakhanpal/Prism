-- The parts of each try of the nightly job's score task (ticket 89; strata.lakehouse.nightly, _score): a row for
-- each part the try ran, with when it started and finished, and a row for each part it left for the next night
-- once the task's minutes were spent (config/thresholds.toml, nightly.score_minutes). The next try reads the rows
-- of the latest try and runs the parts it left first.
--
-- run_id        the job run's id, as in strata.ops.pipeline_runs
-- task_started  when the try of the score task started, in UTC, which tells two tries of one run apart
-- position      the part's place in the try's order, from 1
-- part          the part, as strata.lakehouse.nightly.SCORE_PARTS names it
-- state         ran, or left
-- rows_changed  the rows the part added, changed or removed; empty for a part left
-- started_at    when the part started, in UTC: when the part before it finished; empty for a part left
-- finished_at   when the part finished, in UTC; empty for a part left
-- public_from   the day the row was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.score_parts (
  run_id STRING NOT NULL,
  task_started TIMESTAMP NOT NULL,
  position BIGINT NOT NULL,
  part STRING NOT NULL,
  state STRING NOT NULL,
  rows_changed BIGINT,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  public_from DATE NOT NULL
)
