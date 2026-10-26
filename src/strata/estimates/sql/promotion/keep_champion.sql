-- Promotion (ticket 44): the promoted version kept again under the champion alias, from its challenger row, so the
-- score task and the app, which read the newest champion row, score with it from the day it was promoted. The
-- challenger row stays; rows are only ever added.
INSERT INTO strata.gold.time_estimate_model
SELECT m.model, m.version, :alias AS alias, m.training_through, m.booster_json, m.state_json, m.mlflow_run_id,
  :registered_at AS registered_at, :public_from AS public_from
FROM strata.gold.time_estimate_model AS m
WHERE m.model = :model
  AND m.version = :version
  AND m.alias = :from_alias
QUALIFY row_number() OVER (ORDER BY m.registered_at DESC) = 1
