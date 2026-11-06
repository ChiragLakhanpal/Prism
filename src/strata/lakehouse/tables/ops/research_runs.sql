-- One row for each deep research run on a project (ticket 147): which sources Prism asked, which answered, and what
-- the run says about them. Written as the app's own service principal (src/strata/research/store.py), after the
-- run's items in strata.ops.research_items, so a reader that finds a run finds every item it read. A run that fails
-- part way leaves items no run names, which no read returns and which the store removes with a DELETE that names the
-- run (CLAUDE.md rule 5).
--
-- run_id         the run's id; the demo seed's is seed:<project>:<as_of>
-- project_id     the project researched
-- started        when the run started, in UTC
-- finished       when the run finished, in UTC
-- as_of          the day the run reads as of (ADR 0002): no item made public after it is kept
-- viewer         the user id the Databricks App forwarded for the person who asked, or prism for the seed
-- sources_asked  the registry keys of the sources asked, as a JSON list (config/research.toml)
-- reached        the registry keys of the sources that answered, as a JSON list
-- note           one or two sentences on the run, such as the day its items were read
-- source_notes   each source's status, its note and how many items it gave, as JSON by source key
-- public_from    the run's as_of (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.research_runs (
  run_id STRING NOT NULL,
  project_id STRING NOT NULL,
  started TIMESTAMP NOT NULL,
  finished TIMESTAMP,
  as_of DATE NOT NULL,
  viewer STRING,
  sources_asked STRING NOT NULL,
  reached STRING NOT NULL,
  note STRING,
  source_notes STRING,
  public_from DATE NOT NULL
)
