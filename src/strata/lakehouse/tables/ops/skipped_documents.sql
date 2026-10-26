-- One row for each document, or project's document list, that a document run skipped because it could not
-- fetch or read it (ticket 72). The run writes the row when it skips, keeps what it read before, and goes on
-- with the next document, so one failed fetch no longer stops the run. A later run tries the document again.
-- The plan reader and the passage reader write here (src/strata/lakehouse/readers.py and passages.py).
--
-- run_id       the run that skipped it
-- reader       the reader that skipped it: plans (the plan reader) or passages (the passage reader)
-- project_id   the project whose document or list it is
-- document_id  the document; empty when the run could not fetch the project's document list
-- url          the address the run could not fetch or read
-- reason       why, in the words of the error the run met
-- skipped_at   when, in UTC
-- public_from  the day it was skipped, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.skipped_documents (
  run_id STRING NOT NULL,
  reader STRING NOT NULL,
  project_id STRING NOT NULL,
  document_id STRING,
  url STRING NOT NULL,
  reason STRING NOT NULL,
  skipped_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
