-- The estimates loop (ticket 44): when the time estimate was last trained and registered, under any alias, and the
-- newest retrain the watch raised, which together say whether a retrain is due.
SELECT
  (SELECT max(m.registered_at) FROM strata.gold.time_estimate_model AS m WHERE m.model = :model) AS registered_at,
  (SELECT max(t.raised_at) FROM strata.ops.retrain_triggers AS t WHERE t.model = :model) AS raised_at,
  CAST(:as_of AS DATE) AS public_from
