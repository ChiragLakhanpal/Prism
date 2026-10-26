-- The estimates loop (ticket 44): the time estimate's champion as public on :as_of, without its trees: the newest
-- version kept with the champion alias (strata.gold.time_estimate_model; a promotion keeps a new champion row).
SELECT m.model, m.version, m.training_through, m.registered_at, m.public_from
FROM strata.gold.time_estimate_model AS m
WHERE m.model = :model
  AND m.alias = :alias
  AND m.public_from <= :as_of
ORDER BY m.registered_at DESC, m.version DESC
LIMIT 1
