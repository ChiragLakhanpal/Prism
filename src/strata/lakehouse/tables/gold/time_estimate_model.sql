-- Each version of the time estimate's model that the replay harness registered (ticket 25), in a form the
-- app and the nightly job can read without MLflow or XGBoost (ticket 26): XGBoost's own JSON model and the
-- model's state (its ranges' offsets, its vocabularies and the feature ranges it learned from). The registry
-- in Unity Catalog stays the model's home, with its champion and challenger aliases; this table is the copy
-- the score task scores with, and estimate_time scores a package with when it has no stored score, such as
-- a package planned from a sentence a moment ago (src/strata/estimates/portable.py). A version is written
-- once, when it is registered, and never changed.
--
-- model             the model's three-part name in Unity Catalog, config/models.toml's registered_model
-- version           its version there
-- alias             the alias it was registered with: champion or challenger
-- training_through  the day its training data ended: it gives no time estimate as of an earlier day
-- booster_json      XGBoost's JSON model (Booster.save_raw("json"))
-- state_json        the rest of the model (TimeEstimateModel.state_json)
-- mlflow_run_id     the MLflow run that logged it with its model card
-- registered_at     when the harness registered it, in UTC
-- public_from       the day it was registered (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.time_estimate_model (
  model STRING NOT NULL,
  version INT NOT NULL,
  alias STRING NOT NULL,
  training_through DATE NOT NULL,
  booster_json STRING NOT NULL,
  state_json STRING NOT NULL,
  mlflow_run_id STRING,
  registered_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
