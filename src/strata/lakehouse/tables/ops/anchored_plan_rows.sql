-- The plan rows published after Prism showed a range for their package (ticket 44; the 45 design brief, section
-- 7.2, tiles 9, 30 and 35), as each monthly watch of the estimates loop found them (src/strata/estimates/watch.py).
-- A row is dated within estimates_loop.anchored_within_days of a date Prism offered when its planned signing date
-- (the Signed Contract step's planned_on in strata.silver.plan_steps) is that close to the middle or the 8-in-10
-- point of an exposure (strata.ops.exposures) made before the row's plan version was published. Screens call these
-- "Plan rows dated within 14 days of a date I offered" and never "anchored" (the 45 design brief). Each watch
-- appends its own rows; nothing is replaced.
--
-- run_id              the watch's run
-- month               the last day of the watched month: the rows are as of that day
-- document_id         the plan version (strata.silver.plan_versions)
-- project_id          its project
-- step_reference      the package's STEP reference (Activity Reference No.)
-- published_on        the plan version's public date
-- planned_signing_on  the row's Signed Contract Planned date
-- exposure_id         the exposure whose offered date is nearest the planned signing date
-- exposed_on          the day of that exposure
-- offered_on          that offered date: the middle or the 8-in-10 point
-- days_from_offered   whole days between offered_on and planned_signing_on, early or late
-- anchored            whether days_from_offered is anchored_within_days or fewer
-- country_code        the project's country
-- using_strata        whether the country was using Prism when the version was published (config/slice.toml)
-- contract_signed_on  the package's actual signing date (strata.gold.package), when signed by month; never a plan's
--                     Actual column, since the two can disagree
-- days_from_plan      whole days between planned_signing_on and contract_signed_on, early or late
-- measured_at         when the watch ran, in UTC
-- public_from         the day the watch ran (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.anchored_plan_rows (
  run_id STRING NOT NULL,
  month DATE NOT NULL,
  document_id STRING NOT NULL,
  project_id STRING,
  step_reference STRING NOT NULL,
  published_on DATE NOT NULL,
  planned_signing_on DATE NOT NULL,
  exposure_id STRING NOT NULL,
  exposed_on DATE NOT NULL,
  offered_on DATE NOT NULL,
  days_from_offered INT NOT NULL,
  anchored BOOLEAN NOT NULL,
  country_code STRING,
  using_strata BOOLEAN NOT NULL,
  contract_signed_on DATE,
  days_from_plan INT,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
