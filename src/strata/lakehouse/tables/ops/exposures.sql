-- The exposure log (ticket 44; docs/PLAN.md section 11, "Loops through the world"): one row each time the server
-- sent a viewer a past range or a time estimate for a package with a STEP reference, in the World Bank staff view.
-- A range shown in a preview is not an exposure, and an abstention shows no range, so neither writes a row (the 45
-- design brief, decision 13). The replay harness, batch scoring, the hindsight test and the nightly job call the
-- same tools and never write here: only the server's routes do (src/strata/estimates/exposures.py): the estimate
-- and comparables routes, and POST /api/ask for each range a sentence the verifier kept cited.
--
-- This is the one place "exposed to Prism" is defined (CLAUDE.md rule 4): the hindsight test's gate set
-- (src/strata/estimates/sql/hindsight/exposed.sql) and the estimates loop's anchored plan rows
-- (src/strata/estimates/watch.py, marked_rows) both read it. The app writes it as its own service principal,
-- with the viewer's user id, never their email, because every account user can read strata.ops. Rows only join.
--
-- exposure_id              a random id
-- shown_at                 when the server sent the range, in UTC
-- exposed_on               that day
-- viewer_id                the viewer's user id, as the Databricks App forwarded it
-- view                     the view the range was shown in: staff
-- route                    the route that sent it: /api/packages/{step_reference}/estimate, /comparables or /api/ask
-- as_of                    the as-of date the tool was called with
-- step_reference           the package's STEP reference
-- project_id, country_code the package's project and its country, from its newest public plan row
-- shown                    past_range (find_comparables) or time_estimate (estimate_time)
-- range_shown              the points shown, as JSON: q25, q50, q75 and q80 in months, and days with the same keys
-- model, model_version     the time estimate's model and version; empty for a past range
-- option_chosen            the plan-date choice: middle or eight_in_ten (the 26 design brief, section 6.3)
-- option_saved             whether the viewer saved that choice; false when it is the cautious default
-- start_date               the day the offered dates count from
-- start_from               first_notice (the package's first specific procurement notice, when it was public by
--                          as_of) or planned_notice (the newest public plan row's planned notice date); empty
--                          when the package has neither, and then no date was offered
-- offered_middle_on        start_date plus the middle (q50) in days
-- offered_eight_in_ten_on  start_date plus the 8-in-10 point (q80) in days
-- public_from              exposed_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.exposures (
  exposure_id STRING NOT NULL,
  shown_at TIMESTAMP NOT NULL,
  exposed_on DATE NOT NULL,
  viewer_id STRING,
  view STRING NOT NULL,
  route STRING NOT NULL,
  as_of DATE NOT NULL,
  step_reference STRING NOT NULL,
  project_id STRING,
  country_code STRING,
  shown STRING NOT NULL,
  range_shown STRING NOT NULL,
  model STRING,
  model_version INT,
  option_chosen STRING NOT NULL,
  option_saved BOOLEAN NOT NULL,
  start_date DATE,
  start_from STRING,
  offered_middle_on DATE,
  offered_eight_in_ten_on DATE,
  public_from DATE NOT NULL
)
