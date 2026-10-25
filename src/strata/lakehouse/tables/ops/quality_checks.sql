-- The quality checks each task of the nightly job ran when it finished (ticket 43; the 45 brief, section 6):
-- one row per check, passed or failed, for the dashboard's Governance page. config/quality_checks.toml names
-- the tables each task checks, and config/thresholds.toml [quality_checks] their expected row counts
-- (strata.lakehouse.quality). A rerun of a task writes its own rows under the same run, so every try keeps its
-- checks. The rows hold codes and counts only: the page's words are the dashboard's (dash.gov.check.*).
--
-- run_id         the job run's id, as strata.ops.pipeline_runs holds it
-- night          the night of the run: the day, in the job's time zone (bundle/nightly.yml), its first task
--                started
-- task_key       the task that ran the check, as bundle/nightly.yml names it
-- check_kind     row_count, missing_key, missing_public_from, duplicates or contacts_left
-- table_name     the table checked, in three parts
-- key_name       for missing_key: the key column the rows miss
-- found          what the check counted: the table's rows for row_count, the rows that miss the key or the
--                Disclosed date, the rows that repeat a key beyond its first, or the notices still carrying
--                an email address or a labelled phone number
-- expected_min   for row_count: the fewest rows expected
-- expected_max   for row_count: the most rows expected
-- passed         whether the count is what the check expects: inside the range, or 0 for the other checks
-- checked_at     when, in UTC
-- public_from    the day it was checked, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.quality_checks (
  run_id STRING NOT NULL,
  night DATE NOT NULL,
  task_key STRING NOT NULL,
  check_kind STRING NOT NULL,
  table_name STRING NOT NULL,
  key_name STRING,
  found BIGINT NOT NULL,
  expected_min BIGINT,
  expected_max BIGINT,
  passed BOOLEAN NOT NULL,
  checked_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
