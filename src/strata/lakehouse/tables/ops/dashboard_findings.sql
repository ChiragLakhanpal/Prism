-- "What the measures say" on the dashboard's Governance and AI quality and adoption pages (ticket 45; the 45 design
-- brief, sections 6.3 and 7.3): one sentence per section, written from the copy file's templates by the job that
-- takes the section's measures, for a fixed period the sentence names (strata.dashboard.findings). Each write appends
-- its rows; the dashboard reads each section's newest. The page filters never change a sentence.
--
-- run_id       the run that wrote it: the nightly job's run, or the daily cost pull's for Azure spend
-- page         governance or ai
-- section      the section's key, such as runs, spend, benchmark or estimates
-- position     its place on the page, from 1
-- about        the section's name, as the table's About column shows it
-- finding      the sentence or sentences, as the copy file writes them
-- measured_on  the day its measure was taken; empty before the first measure
-- written_at   when it was written, in UTC
-- public_from  the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.dashboard_findings (
  run_id STRING NOT NULL,
  page STRING NOT NULL,
  section STRING NOT NULL,
  position INT NOT NULL,
  about STRING NOT NULL,
  finding STRING NOT NULL,
  measured_on DATE,
  written_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
