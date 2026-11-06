-- One row for each deep research brief Prism wrote and checked (ticket 148): the writer's sections, the sentences
-- the verifier kept with the evidence they cite, the sentences it removed with their reasons, and the run's
-- coverage. GET /api/projects/{project_id}/research answers with the latest row for the project, so a second view
-- calls no model; "Research again" starts a new run and a new row. The run writes it as the app's own service
-- principal on the workspace, and in the local DuckDB file on this computer (src/strata/research/briefs.py). The
-- brief rests on public items, so every view may read it.
--
-- run_id       the run it was written from, in strata.ops.research_runs
-- project_id   the project, such as P156634
-- written_at   when the verifier finished, in UTC
-- as_of        the day the run read the sources as of
-- brief        the brief as JSON: its sections, the evidence its sentences cite, the verifier's counts, the removed
--              sentences, the run's coverage and the writer
-- public_from  the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.research_briefs (
  run_id STRING NOT NULL,
  project_id STRING NOT NULL,
  written_at TIMESTAMP NOT NULL,
  as_of DATE NOT NULL,
  brief STRING NOT NULL,
  public_from DATE NOT NULL
)
