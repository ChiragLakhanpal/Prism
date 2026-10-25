-- estimate_time: one package's stored time estimates, as described and for each what-if combination, from
-- the latest scoring run public on the as-of date (ADR 0002). The nightly score task appends a run's rows
-- under its run_id (src/strata/estimates/scoring.py), so the latest run is the one scored last.
WITH latest AS (
  SELECT run_id, max(scored_at) AS scored_at
  FROM strata.gold.time_estimate_score
  WHERE step_reference = :step_reference AND public_from <= :as_of
  GROUP BY run_id
  ORDER BY scored_at DESC, run_id DESC
  LIMIT 1
)
SELECT s.step_reference, s.run_id, s.as_described, s.market_approach, s.prequalification, s.review_type,
  s.estimated_amount_usd, s.feature_date, s.q25_days, s.q50_days, s.q75_days, s.q80_days, s.q25_months, s.q50_months,
  s.q75_months, s.q80_months, s.abstention, s.abstention_detail, s.features_json, s.model, s.model_version, s.model_alias,
  s.training_through, s.scored_at, s.public_from
FROM strata.gold.time_estimate_score AS s
JOIN latest AS l ON l.run_id = s.run_id
WHERE s.step_reference = :step_reference
ORDER BY s.as_described DESC, s.market_approach, s.prequalification
