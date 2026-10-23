-- One row for each page the layout parser (Route B) tried and could not read. The run leaves the
-- page out of bronze.layout_pages and goes on to the next page. The attempt counts against the
-- daily page cap, and the page waits until the next day, in UTC, before a run tries it again.
--
-- run_id       the run that tried it
-- project_id   the project whose document it is
-- document_id  the document
-- pdf_page     the page's number in the PDF
-- page_hash    the hash of the page's text
-- parser       the layout parser
-- error        what went wrong, in the parser's words
-- failed_at    when, in UTC
-- public_from  the day it failed, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.parse_failures (
  run_id STRING NOT NULL,
  project_id STRING NOT NULL,
  document_id STRING NOT NULL,
  pdf_page INT NOT NULL,
  page_hash STRING NOT NULL,
  parser STRING NOT NULL,
  error STRING NOT NULL,
  failed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
