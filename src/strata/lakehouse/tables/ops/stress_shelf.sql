-- The stress shelf's outcomes: what each document run recovered from each of the hardest documents
-- (src/strata/lakehouse/stress_shelf.py; docs/PLAN.md section 3). One row per shelf entry per run, in
-- config/slice.toml's order. The Data readiness page shows the latest run's rows on or before its as-of
-- date, under "The hardest documents I read", and sets each badge from config/thresholds.toml.
--
-- run_id              the document run
-- shelf_key           the entry's key in config/slice.toml
-- kind                scan_annex, longest_pad, large_plan, other_language or over_parser_limit
-- position            the entry's place on the shelf, from 1
-- state               read; stopped_at_cap (some of its layout parser pages wait for the next run);
--                     not_read (the run has not fetched it); or no_document (no document fits its rule)
-- document_id         the document chosen, in the documents API
-- project_id          its project
-- document_type       its type, word for word
-- document_date       its date (docdt)
-- pdf_pages           its pages, in the PDF
-- pdf_url             where its PDF is, for "Open at page"
-- language            its language, as an ISO 639-1 code
-- part                for scan_annex, the hard part's key in web/src/copy.ts, such as risk_annex
-- hard_page           the PDF page where the hard part starts
-- parser_pages        the pages the page router sent to the layout parser
-- count, denominator  the outcome: what was recovered, out of what the document holds
-- denominator_from    where the denominator comes from: hand_count (a person counted it in the PDF),
--                     pdf_pages, text_references (the activity references its text lists) or
--                     passages_made; empty when there is nothing to check against
-- counted_on          for a hand count, the day a person counted it
-- unreadable          whether the layout parser could read none of the hard part's pages
-- parts               for a document over the layout parser's limit, the parts it was read in
-- parser              the layout parser's name
-- parser_limit_pages  the layout parser's page limit, ingestion.parser_part_pages
-- longest_pages       the most pages of any document the run read
-- read_pages          the pages read so far: published text with text, and layout parser pages read
-- daily_page_cap      the daily page cap the run worked under
-- measured_at         when, in UTC
-- public_from         the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.stress_shelf (
  run_id STRING NOT NULL,
  shelf_key STRING NOT NULL,
  kind STRING NOT NULL,
  position INT NOT NULL,
  state STRING NOT NULL,
  document_id STRING,
  project_id STRING,
  document_type STRING,
  document_date DATE,
  pdf_pages INT,
  pdf_url STRING,
  language STRING,
  part STRING,
  hard_page INT,
  parser_pages INT,
  count BIGINT,
  denominator BIGINT,
  denominator_from STRING,
  counted_on DATE,
  unreadable BOOLEAN NOT NULL,
  parts INT,
  parser STRING,
  parser_limit_pages INT NOT NULL,
  longest_pages INT,
  read_pages INT,
  daily_page_cap INT NOT NULL,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
