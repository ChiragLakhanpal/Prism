-- One row for each run of the layout parser (Route B) over a project's documents: the daily page
-- cap it ran under, how many pages it parsed and how many it could not read, and, when it reached
-- the cap, the first page it left for the next day.
--
-- run_id                    the run
-- project_id                the project whose documents it read
-- parser                    the layout parser
-- daily_page_cap            the cap in config/thresholds.toml (ingestion.daily_page_cap)
-- parsed_earlier_today      pages the parser tried that day, in UTC, before this run started, read or failed
-- pages_waiting             pages chosen for the layout parser, not yet parsed and not failed that day, at the start
-- pages_parsed              pages this run parsed
-- pages_failed              pages this run tried and could not read (each one is in strata.ops.parse_failures)
-- first_failed_document_id  the document of the first page it could not read
-- first_failed_pdf_page     that page's number in the PDF
-- stopped_at_cap            whether the run stopped because it reached the cap
-- stopped_at_document_id    the document of the first page it did not try, when it stopped
-- stopped_at_pdf_page       that page's number in the PDF
-- started_at, finished_at   when the run started and finished, in UTC
-- public_from               the day it finished, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.parse_runs (
  run_id STRING NOT NULL,
  project_id STRING NOT NULL,
  parser STRING NOT NULL,
  daily_page_cap BIGINT NOT NULL,
  parsed_earlier_today BIGINT NOT NULL,
  pages_waiting BIGINT NOT NULL,
  pages_parsed BIGINT NOT NULL,
  pages_failed BIGINT NOT NULL,
  first_failed_document_id STRING,
  first_failed_pdf_page INT,
  stopped_at_cap BOOLEAN NOT NULL,
  stopped_at_document_id STRING,
  stopped_at_pdf_page INT,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
