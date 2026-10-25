-- The risks a viewer selected for the borrower's PPSD on a package workspace's section 3, procurement risks and
-- what helped (ticket 30): one row per viewer, package and risk, made the first time the viewer selects that
-- risk and changed with a MERGE each time after, so unselecting a risk sets selected to false and never deletes
-- a row. A package from a STEP row keeps a selection per viewer and STEP reference (the 27 brief's rule); a
-- package from a sentence keeps its author's selection with the package. It is app state, read each time the
-- workspace opens, so it lives in Lakebase (ADR 0005). The server writes it as the app's own service principal,
-- naming the viewer the Databricks App forwarded; a preview of another view writes nothing. A selected risk that
-- leaves the table stays here, and the section names it and does not count it. Ticket 36 drafts PPSD rows from
-- the selected risks on screen.
--
-- viewer_id     the user id the Databricks App forwarded
-- package_kind  step_reference, for a package from a STEP row, or planned, for a package from a sentence
-- package_key   the STEP reference, or the planned package's id (strata.app.planned_packages)
-- risk_key      the risk factor's key in config/lessons.toml, which never changes once used
-- selected      whether the risk is selected now
-- saved_at      when the viewer last selected or unselected it, in UTC
-- public_from   the day the viewer first selected it, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.app.risk_selections (
  viewer_id STRING NOT NULL,
  package_kind STRING NOT NULL,
  package_key STRING NOT NULL,
  risk_key STRING NOT NULL,
  selected BOOLEAN NOT NULL,
  saved_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
