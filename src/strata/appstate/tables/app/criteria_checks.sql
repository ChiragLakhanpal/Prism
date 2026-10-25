-- Each run of "Check your criteria", section 5 of the package workspace (ticket 31), one row per run so nothing is
-- rewritten: the package-level run (rejected bids, the cost estimate and the lessons, checked) and each comparison
-- of a person's pasted qualification criteria. It is app state, so it lives in Lakebase (ADR 0005), and the
-- check-your-criteria workflow writes it as the app's own service principal.
--
-- Pasted text is treated like an upload (CLAUDE.md rule 8; the 31 brief, section 5.3): every read filters on
-- owner_id (src/strata/criteria/sql/), so a person's text and results are never read for anyone else. The text
-- never goes in an address or the evidence-open log. A package-level run reads only public records, but it is
-- kept per person too, so one query reads both.
--
-- check_id               the run's id, in its evidence ids: paste:{check_id}
-- owner_id               the user id the Databricks App forwarded for the person, bound per request
-- package_key            step:{STEP reference} for a package from a plan row, planned:{package_id} for one planned
--                        from a sentence
-- kind                   package_run or comparison
-- pasted_text            the qualification criteria the person pasted, for a comparison; empty for a package run
-- status                 running (the text was saved when the person pressed "Compare the criteria"), ready,
--                        refused, failed or content_filtered
-- result                 what the run found, as JSON, as the section shows it; empty while running
-- comparables_signature  which comparable packages it used, so a saved run is shown only while they are the same
-- records_through        the day the records it read run through
-- created_at             when the row was written, in UTC; the newest row of a package and kind is the run now
-- public_from            the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.app.criteria_checks (
  check_id STRING NOT NULL,
  owner_id STRING NOT NULL,
  package_key STRING NOT NULL,
  kind STRING NOT NULL,
  pasted_text STRING,
  status STRING NOT NULL,
  result STRING,
  comparables_signature STRING,
  records_through DATE,
  created_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
