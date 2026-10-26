-- Each tool call of each answer run, in call order (ticket 45; the 45 brief, section 6.2, tile 25): the step from
-- an answer's run ID to the tools it called, for the dashboard's lineage. The run log (src/strata/agent/runs.py)
-- writes them beside the run's row in strata.ops.agent_runs, as the app's own service principal.
--
-- An input that names a private upload never reaches this table: its value is written as "a private upload"
-- (copy.dash.gov.privateUpload), and private_upload marks the call, so the dashboard shows neither the upload nor
-- the run's question (the 45 brief, section 11).
--
-- run_id          the answer run (strata.ops.agent_runs)
-- call_order      1 for the run's first call
-- round           the round of tool calls it ran in
-- tool            its name in the tool registry, such as find_comparables
-- inputs          its arguments, as name: value pairs
-- rows_returned   how many rows it returned
-- took_ms         how long the call took, in milliseconds
-- evidence_ids    the evidence ids of the rows it returned, joined by commas
-- abstention      the reason it gave no rows or no range, as the registry lists it; empty when it answered
-- error           why the call did not run: bad_arguments, permission or round_limit; empty when it ran
-- private_upload  whether an input named a private upload
-- called_at       when it started, in UTC
-- public_from     the day of the run, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.tool_calls (
  run_id STRING NOT NULL,
  call_order INT NOT NULL,
  round INT,
  tool STRING NOT NULL,
  inputs STRING NOT NULL,
  rows_returned INT,
  took_ms INT,
  evidence_ids STRING,
  abstention STRING,
  error STRING,
  private_upload BOOLEAN NOT NULL,
  called_at TIMESTAMP,
  public_from DATE NOT NULL
)
