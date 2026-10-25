-- The rebidding champion's natural frequency for each package (ticket 28), scored in batch by the nightly job's
-- score task (strata.estimates.rebidding_backtest.score_packages): one row per package per run. rebidding_risk
-- reads a package's newest score with the champion's version and shows it only when the champion beat its
-- baseline and the package has 20 or more comparables.
--
-- run_id         the run that scored
-- step_reference the package
-- model          the champion's three-part name in Unity Catalog, such as strata.gold.rebidding_risk
-- version        its version there
-- learner        gbm (calibrated gradient boosting) or logistic (logistic regression)
-- probability    the chance it gave that a package like this one is advertised again, from 0 to 1
-- in10           the same, as a whole number in 10, rounded half up: what "about k in 10" states
-- scored_on      the day the features were read as of
-- public_from    the day it was scored (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.rebidding_scores (
  run_id STRING NOT NULL,
  step_reference STRING NOT NULL,
  model STRING NOT NULL,
  version INT NOT NULL,
  learner STRING NOT NULL,
  probability DOUBLE NOT NULL,
  in10 INT NOT NULL,
  scored_on DATE NOT NULL,
  public_from DATE NOT NULL
)
