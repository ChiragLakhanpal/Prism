-- The Data readiness page as data_readiness_for built it for one day, written by every run that
-- measures data readiness (ticket 16), so the dashboard's Data readiness page shows the same
-- headline, statuses and fixes as the app for the same date without a second definition of them
-- (CLAUDE.md rule 4). The dashboard reads the newest snapshot on or before the date it is set to.
--
-- run_id         the run that wrote it; "fixture" in the gate's fixture database
-- measured_on    the date the page was built as of
-- part           headline (the day's headline sentence), source (one row of the Sources table),
--                gap (a known gap no dataset fills), fix (one ranked fix), link (one linked share),
--                route (the pages each reading route read well), or award_year and source_year (a
--                source's rows in one fiscal year, counted as its Coverage cell counts them, so its
--                years add up to that number; award_year for the contract-award datasets)
-- position       the row's place within its part: the registry's order, or a fix's rank
-- label          what the row names, such as "Contract awards, since fiscal 2020"
-- text           the headline, a fix's sentence, a known gap's note, a link's or a route's counts
--                as tables write them ("22 of 22"), or a fiscal year as the dashboard writes it (FY20)
-- status         Partial or Gap, in words, for a source or gap row that has one; otherwise empty
-- latest_data    for a source: the date its freshness measure gives
-- updates        for a source: how often it updates, such as daily, frozen or as published
-- days_late      for a source that is late: how many days; otherwise empty
-- count          for a source, a link or a route: the measure's count; for a fiscal year, its rows
-- denominator    and its denominator
-- share_percent  the whole percent, as data_readiness_for rounds it, only from
--                data_readiness.fewest_for_a_percentage rows
-- projects       for a fix: the projects it would add evidence to
-- fiscal_year    for award_year and source_year: the fiscal year, or empty for rows with none
-- written_at     when, in UTC
-- public_from    the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.readiness_snapshot (
  run_id STRING NOT NULL,
  measured_on DATE NOT NULL,
  part STRING NOT NULL,
  position INT NOT NULL,
  label STRING,
  text STRING,
  status STRING,
  latest_data DATE,
  updates STRING,
  days_late INT,
  count BIGINT,
  denominator BIGINT,
  share_percent INT,
  projects BIGINT,
  fiscal_year INT,
  written_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
