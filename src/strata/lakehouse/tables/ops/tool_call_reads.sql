-- Each table each tool call read (ticket 45; the 45 brief, section 6.2, tile 26): the last step of lineage, from an
-- answer's run ID to its tool calls to the tables they read. The tool registry notes every table a call's queries
-- name (strata.tools.registry, Context.reads), and the run log writes one row per call and table.
--
-- run_id        the answer run (strata.ops.agent_runs)
-- call_order    the call, as strata.ops.tool_calls numbers it
-- tool          the call's tool
-- table_name    the table or view it read, in three parts
-- version_read  the table's Delta version when the call read it, from its history; empty on DuckDB, which keeps no
--               versions, and when the history could not be read
-- sources       the source registry's names for the sources the tool reads (config/tools.toml, sources)
-- read_at       when the call read it, in UTC
-- public_from   the day of the run, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.tool_call_reads (
  run_id STRING NOT NULL,
  call_order INT NOT NULL,
  tool STRING NOT NULL,
  table_name STRING NOT NULL,
  version_read BIGINT,
  sources STRING,
  read_at TIMESTAMP,
  public_from DATE NOT NULL
)
