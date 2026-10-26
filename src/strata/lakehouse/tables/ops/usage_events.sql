-- One row for each request a viewer makes to the app for a page or an /api route (ticket 06), for
-- the adoption measures on the dashboard's AI quality and adoption page, such as weekly users. The
-- server leaves out /api/health, which the platform calls, and the files a page loads. It writes
-- the rows as the app's own service principal, a few at a time (src/strata/server/usage.py).
--
-- The rows keep no email: every account user can read strata.ops (bundle/catalog.yml), and the
-- user id is enough to count people. The web app changes pages without asking the server, so a
-- visit records the page it starts on and the /api routes it calls (/api/me and /api/freshness on
-- every full page load). A count of pages keeps only route NOT LIKE '/api/%'.
--
-- viewer_id     the user id the Databricks App forwarded; empty when no one was signed in
-- route         the path asked for, without its query, such as /projects/P130164 or /api/freshness
-- view          the view the server bound for the request (ticket 40): piu or public in a preview, else staff
-- requested_at  when the request arrived, in UTC
-- trace_id      the request's trace in Application Insights, as 32 hex digits
-- public_from   the day of the request, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.usage_events (
  viewer_id STRING,
  route STRING NOT NULL,
  view STRING NOT NULL,
  requested_at TIMESTAMP NOT NULL,
  trace_id STRING,
  public_from DATE NOT NULL
)
