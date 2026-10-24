-- One row for each viewer and each source they opened in the evidence drawer (ticket 14): from a citation
-- marker, a number, the source switcher, a table row or a link. The evidence pack's export (ticket 35)
-- reads it for "You opened 3 of 14 sources". The server writes it as the app's own service principal
-- (src/strata/server/evidence.py), one MERGE per open, so a second open of the same source updates its
-- row. A preview of another view writes nothing.
--
-- The rows keep no email: every account user can read strata.ops (bundle/catalog.yml), and the user id
-- is enough to tell people apart.
--
-- viewer_id        the user id the Databricks App forwarded
-- evidence_id      the source, as the answer stream's evidence event names it, such as
--                  strata.gold.passage:31525018/v1/54
-- first_opened_at  when the viewer first opened it, in UTC
-- last_opened_at   when the viewer last opened it, in UTC
-- times_opened     how many times the drawer showed it to the viewer
-- last_run_id      the answer it was last opened from, or empty when it was opened from a link
-- last_route       the page it was last opened on, such as /projects/P130164
-- public_from      the day it was first opened, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.evidence_opened (
  viewer_id STRING NOT NULL,
  evidence_id STRING NOT NULL,
  first_opened_at TIMESTAMP NOT NULL,
  last_opened_at TIMESTAMP NOT NULL,
  times_opened INT NOT NULL,
  last_run_id STRING,
  last_route STRING,
  public_from DATE NOT NULL
)
