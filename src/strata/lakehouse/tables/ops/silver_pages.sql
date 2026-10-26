-- What silver wrote from each bronze page (ticket 75; strata.lakehouse.silver.run): one row each time a source's
-- silver transform read a page into its tables, written after the last of them, so a run that stops partway leaves
-- the page waiting. A page waits when it has no row here, or when its newest row names other tables or another
-- version than the transform has now. So a transform that gains a table, or bumps its VERSION, reads every page of
-- its source once more, and fills the new table from the pages bronze already holds. Rows are only added: each
-- read of a page keeps its own row.
--
-- source       the source the page came from (config/sources.toml)
-- page_hash    the page, as strata.bronze.api_pages keys it
-- tables       the silver tables the transform wrote the page into, by full name, sorted and joined with commas
-- version      the transform's VERSION, 1 unless the transform sets one
-- written_at   when the page's rows were written, in UTC
-- public_from  the day they were written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.silver_pages (
  source STRING NOT NULL,
  page_hash STRING NOT NULL,
  tables STRING NOT NULL,
  version INT NOT NULL,
  written_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
