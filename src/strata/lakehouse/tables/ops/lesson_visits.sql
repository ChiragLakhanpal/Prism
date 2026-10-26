-- Each time a person opened a Lessons page (ticket 39; the 39 brief, section 4.2), so the page can open on what
-- came in since their last visit. A visit is a session: it starts when the person opens Lessons after
-- lessons.visit_gap_minutes away (config/thresholds.toml), and a reload or a trip to a draft and back stays in the
-- same visit. Each page load adds a row with the start of the visit it belongs to, so no row is ever changed; the
-- latest row says when the person last looked. Previews and as-of views add nothing. The app's own service
-- principal writes and reads it (strata.knowledge.lessons.visits), with the viewer the Databricks App forwarded.
--
-- viewer_id         the person: the user id the Databricks App forwarded
-- visit_started_at  when the visit this page load belongs to started, in UTC
-- seen_at           when the page loaded, in UTC
-- public_from       the day it loaded, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_visits (
  viewer_id STRING NOT NULL,
  visit_started_at TIMESTAMP NOT NULL,
  seen_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
