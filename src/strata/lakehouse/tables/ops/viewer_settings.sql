-- Each viewer's saved choices (ticket 42): the language of answers and drafts they chose in the view popover. Each
-- change is a new row, and the latest wins (src/strata/server/viewer_settings.py), so no row is ever changed or
-- removed. A link's ?lang= never writes here. Written by the app's own service principal, naming the viewer the
-- Databricks App forwarded.
--
-- viewer_id         the user id the Databricks App forwarded
-- working_language  the language they chose, as config/languages.toml codes it: en, fr, es or pt
-- changed_at        when, in UTC
-- public_from       the day it changed, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.viewer_settings (
  viewer_id STRING NOT NULL,
  working_language STRING NOT NULL,
  changed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
