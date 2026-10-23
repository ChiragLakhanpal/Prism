-- How much room each table of the strata catalog takes, measured by every run of the nightly job,
-- so the Governance page can show that structured data stays under its limit
-- (config/thresholds.toml, ingestion.structured_data_limit_bytes; docs/PLAN.md section 3).
--
-- run_id        the run that measured it; "fixture" in the gate's fixture database
-- table_name    the table's three-part name, such as strata.bronze.api_pages
-- structured    false for the tables that hold documents' text and layout (bronze.document_pages,
--               bronze.document_texts and bronze.layout_pages); true for every other table
-- row_count     its rows
-- bytes         the bytes it takes: on Databricks, its Delta files (DESCRIBE DETAIL's sizeInBytes);
--               on DuckDB, the 256 KB blocks it fills in the database file
-- measured_at   when, in UTC
-- public_from   the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.table_sizes (
  run_id STRING NOT NULL,
  table_name STRING NOT NULL,
  structured BOOLEAN NOT NULL,
  row_count BIGINT NOT NULL,
  bytes BIGINT NOT NULL,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
