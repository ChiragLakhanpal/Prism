-- The projects exposed to Strata: one row each time Strata showed a project's package something that could change
-- its plan, such as a past range, a time estimate or its procurement risks. The hindsight test leaves every project
-- here out of its gate set and lists it (ticket 34; src/strata/estimates/sql/hindsight/exposed.sql is the one query
-- that reads it), because a risk Strata showed and the project then avoided never reaches the completion report, so
-- counting it would lower recall for the wrong reason (docs/PLAN.md section 11, "Loops through the world").
-- Ticket 44's exposure log writes these rows, or points that query at its own log. A range shown in a preview is not
-- an exposure (the 45 design brief, decision 13). Rows only ever join.
--
-- project_id      the project
-- exposed_on      the day Strata showed it
-- shown           what Strata showed: past_range, time_estimate or risks
-- step_reference  the package's STEP reference, empty when it had none
-- public_from     exposed_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.exposed_projects (
  project_id STRING NOT NULL,
  exposed_on DATE NOT NULL,
  shown STRING NOT NULL,
  step_reference STRING,
  public_from DATE NOT NULL
)
