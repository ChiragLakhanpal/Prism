-- The projects each World Bank staff viewer follows (ticket 37): one row each time a viewer follows or unfollows
-- a project, so a project is followed while its latest row says so. The server writes it as the app's own
-- service principal (src/strata/server/following.py). Nothing is updated: unfollowing is a new row, and rows
-- leave only through a DELETE with a WHERE (CLAUDE.md rule 5).
--
-- The rows keep no email: every account user can read strata.ops (bundle/catalog.yml), and the user id is
-- enough to tell people apart.
--
-- viewer_id    the user id the Databricks App forwarded
-- project_id   the project, such as P156634
-- following    true when the viewer followed it, false when they unfollowed it
-- changed_at   when, in UTC
-- public_from  the day it changed, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.follows (
  viewer_id STRING NOT NULL,
  project_id STRING NOT NULL,
  following BOOLEAN NOT NULL,
  changed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
