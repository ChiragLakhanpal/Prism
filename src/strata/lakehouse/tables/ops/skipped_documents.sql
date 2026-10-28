-- One row for each document, or project's document list, that a document run skipped because it could not
-- fetch or read it, and for each document a run was reading when it stopped (ticket 72). The run writes the row
-- when it skips, keeps what it read before, and goes on with the next document, so one failed fetch no longer
-- stops the run. A run that stops, because the host refused a request or the night's reading time was spent,
-- keeps the pages it read and lists the document it was reading as unfinished, and each document and project's
-- document list the stop left it no time to reach as not_read (ticket 86). A later run tries the document again.
-- The plan reader also lists, once, each older Procurement Plan that a project's newest plan supersedes, when it
-- reads only the newest (config/thresholds.toml, ingestion.plan_versions; ticket 108); no run tries those again.
-- The plan reader and the passage reader write here (src/strata/lakehouse/plans.py, skip, not_read and supersede).
--
-- run_id       the run that skipped it
-- reader       the reader that met it: plans (the plan reader) or passages (the passage reader)
-- project_id   the project whose document or list it is
-- document_id  the document; empty when the run could not fetch the project's document list
-- url          the address the run could not fetch or read, or the PDF it was reading when it stopped
-- outcome      skipped (the run went on with the next document), unfinished (the run stopped partway through it),
--              not_read (the run stopped before it reached it) or superseded (an older plan the reader does not read)
-- reason       why, in the words of the error the run met
-- skipped_at   when, in UTC
-- public_from  the day it was skipped, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.skipped_documents (
  run_id STRING NOT NULL,
  reader STRING NOT NULL,
  project_id STRING NOT NULL,
  document_id STRING,
  url STRING NOT NULL,
  outcome STRING NOT NULL,
  reason STRING NOT NULL,
  skipped_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
