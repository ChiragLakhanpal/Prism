-- One row for each request a viewer makes to the app for a page or an /api route (ticket 06), for
-- the adoption measures on the dashboard's AI quality and adoption page, such as weekly users. The
-- server leaves out /api/health, which the platform calls, and the files a page loads. It writes
-- the rows as the app's own service principal, a few at a time (src/strata/server/usage.py).
--
-- viewer_email  the email the Databricks App forwarded; empty when no one was signed in
-- viewer_id     the user id the App forwarded; empty when no one was signed in
-- route         the path asked for, without its query, such as /projects/P130164 or /api/freshness
-- view          the view the server applied: staff, until ticket 40 adds piu and public
-- requested_at  when the request arrived, in UTC
-- trace_id      the request's trace in Application Insights, as 32 hex digits
-- public_from   the day of the request, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.usage_events (
  viewer_email STRING,
  viewer_id STRING,
  route STRING NOT NULL,
  view STRING NOT NULL,
  requested_at TIMESTAMP NOT NULL,
  trace_id STRING,
  public_from DATE NOT NULL
)
