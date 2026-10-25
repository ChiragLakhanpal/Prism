-- The date of the first step a viewer gave a package whose plan gives no planned dates, on the package workspace's
-- section 2, "Planned date for each step" (ticket 27; the 27 brief, section 6.2). estimate_time dates every later
-- step from it, so the date is the person's own and Strata never invents one. One row per viewer and package, made
-- the first time and changed with a MERGE each time after, so nothing is deleted. A package from a STEP row keeps
-- a date per viewer and STEP reference; a package from a sentence keeps its author's date. It is app state, read
-- each time the workspace opens, so it lives in Lakebase (ADR 0005). The server writes it as the app's own service
-- principal; a preview writes nothing.
--
-- viewer_id     the user id the Databricks App forwarded
-- package_kind  step_reference, for a package from a STEP row, or planned, for a package from a sentence
-- package_key   the STEP reference, or the planned package's id (strata.app.planned_packages)
-- start_date    the date of the package's first step, as the viewer typed it
-- saved_at      when the viewer last gave it, in UTC
-- public_from   the day the viewer first gave it, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.app.step_start_dates (
  viewer_id STRING NOT NULL,
  package_kind STRING NOT NULL,
  package_key STRING NOT NULL,
  start_date DATE NOT NULL,
  saved_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
