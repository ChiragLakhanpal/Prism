-- Every save of a planned package's criteria (ticket 15), one row per change, so its history is never
-- rewritten: the first when the package is made, then one each time its author changes a chip or its
-- plan. The latest row is the package now. It is app state, in Lakebase beside strata.app.planned_packages
-- (ADR 0005). The plan-a-package workflow writes each row as the app's own service principal.
--
-- package_id         the package, in strata.app.planned_packages
-- save_id            this save's id; of two saves at the same moment, the greater id is the later
-- criteria           the criteria as JSON: each field of the package form schema (config/package_form.toml)
--                    with its value and where the value came from (sentence, default, guess, computed or
--                    you), and the review type and market approach that changed because of this save
-- plan_months        the person's plan, in months from bid notice to signed contract, or empty
-- plan_before_range  whether the person entered the plan before Strata showed them the past range, for the
--                    share of plans anchored on Strata's ranges; empty until they enter one
-- saved_at           when it was saved, in UTC
-- public_from        the day it was saved, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.app.planned_package_saves (
  package_id STRING NOT NULL,
  save_id STRING NOT NULL,
  criteria STRING NOT NULL,
  plan_months DOUBLE,
  plan_before_range BOOLEAN,
  saved_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
