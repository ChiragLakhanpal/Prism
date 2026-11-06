-- The plan date a viewer chose for the dates Prism drafts for a package (ticket 26; the 26 design brief,
-- section 6.3, and the 27 brief, section 6.3): the time estimate's middle or its 8-in-10 point. The package
-- workspace's "Dates I draft for this package", under section 1's chart, and section 2's "Date each step with"
-- (ticket 27) are one choice, so both read and write this row. One row per viewer and package, made the first
-- time the viewer chooses and changed with a MERGE each time after, so nothing is deleted. A package from a STEP
-- row keeps a choice per viewer and STEP reference; a package from a sentence keeps its author's choice with the
-- package (the 30 brief's split). With no row, the cautious 8-in-10 point is the default. It is app state, read
-- each time the workspace opens, so it lives in Lakebase (ADR 0005); ticket 44 logs it as the option chosen with
-- each exposure. The server writes it as the app's own service principal; a preview writes nothing.
--
-- viewer_id     the user id the Databricks App forwarded
-- package_kind  step_reference, for a package from a STEP row, or planned, for a package from a sentence
-- package_key   the STEP reference, or the planned package's id (strata.app.planned_packages)
-- choice        middle or eight_in_ten
-- saved_at      when the viewer last chose, in UTC
-- public_from   the day the viewer first chose, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.app.plan_date_choices (
  viewer_id STRING NOT NULL,
  package_kind STRING NOT NULL,
  package_key STRING NOT NULL,
  choice STRING NOT NULL,
  saved_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
