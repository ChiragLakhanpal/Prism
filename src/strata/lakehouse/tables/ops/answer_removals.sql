-- Each sentence the verifier removed from an answer, by the reason it gave first (ticket 45; the 45 brief, section
-- 7.2, tiles 15 and 17). The run log writes them beside the run's row, with the reason code only: the sentence
-- itself stays in strata.ops.agent_runs, so the dashboard counts reasons without showing what an answer said.
--
-- run_id       the answer run (strata.ops.agent_runs)
-- position     1 for the run's first removed sentence
-- reason       the verifier's code (src/strata/agent/verifier.py, REASONS), such as number_not_in_records
-- removed_at   when the run ended, in UTC
-- public_from  the day the run ended, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.answer_removals (
  run_id STRING NOT NULL,
  position INT NOT NULL,
  reason STRING NOT NULL,
  removed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
