-- The estimates loop (ticket 44): when the time estimate was last trained, and the newest retrain the watch raised,
-- which together say whether a retrain is due. A training is the first row kept for a version, under any alias: a
-- promotion keeps the same version again under the champion alias (promotion/keep_champion.sql), which is no
-- training, so it neither restarts the quarter nor clears a retrain raised after that version was trained.
SELECT
  (SELECT max(v.trained_at)
   FROM (SELECT m.version, min(m.registered_at) AS trained_at
         FROM strata.gold.time_estimate_model AS m
         WHERE m.model = :model
         GROUP BY m.version) AS v) AS registered_at,
  (SELECT max(t.raised_at) FROM strata.ops.retrain_triggers AS t WHERE t.model = :model) AS raised_at,
  CAST(:as_of AS DATE) AS public_from
