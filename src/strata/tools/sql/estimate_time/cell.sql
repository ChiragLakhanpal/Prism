-- estimate_time: one stored what-if combination of one package, from the latest scoring run public on the
-- as-of date: the lookup a comparison makes (ticket 26). An empty market approach or qualification matches a
-- row that has none, as the package as described may have none recorded.
WITH latest AS (
  SELECT run_id, max(scored_at) AS scored_at
  FROM strata.gold.time_estimate_score
  WHERE step_reference = :step_reference AND public_from <= :as_of
  GROUP BY run_id
  ORDER BY scored_at DESC, run_id DESC
  LIMIT 1
)
SELECT s.step_reference, s.run_id, s.as_described, s.market_approach, s.prequalification, s.q25_days, s.q50_days,
  s.q75_days, s.q80_days, s.q25_months, s.q50_months, s.q75_months, s.q80_months, s.abstention, s.public_from
FROM strata.gold.time_estimate_score AS s
JOIN latest AS l ON l.run_id = s.run_id
WHERE s.step_reference = :step_reference
  AND (s.market_approach = :market_approach OR (s.market_approach IS NULL AND CAST(:market_approach AS STRING) IS NULL))
  AND (s.prequalification = :prequalification OR (s.prequalification IS NULL AND CAST(:prequalification AS STRING) IS NULL))
ORDER BY s.as_described
LIMIT 1
