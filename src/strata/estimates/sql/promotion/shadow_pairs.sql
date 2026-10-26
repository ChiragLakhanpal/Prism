-- Promotion (ticket 44): the shadow quarter's comparison. Each package that signed after the challenger's first
-- night in shadow (:start) and by :as_of, with each model's first estimate of it made from :start on and by its
-- signing day: the challenger's from strata.ops.time_estimate_shadow and the champion's from
-- strata.gold.time_estimate_score. Only packages both models scored are compared.
WITH finished AS (
  SELECT k.step_reference, k.first_notice_date, k.contract_signed_on, k.public_from
  FROM strata.gold.package AS k
  WHERE k.contract_signed_on > :start
    AND k.contract_signed_on <= :as_of
    AND k.first_notice_date IS NOT NULL
    AND k.first_notice_date <= k.contract_signed_on
),
challenger AS (
  SELECT s.step_reference, s.q50_days, s.q80_days,
    row_number() OVER (PARTITION BY s.step_reference ORDER BY s.scored_at, s.run_id) AS first_estimate
  FROM strata.ops.time_estimate_shadow AS s
  JOIN finished AS f ON f.step_reference = s.step_reference
  WHERE s.model = :model
    AND s.model_version = :challenger
    AND s.q50_days IS NOT NULL
    AND s.public_from >= :start
    AND s.public_from <= f.contract_signed_on
),
champion AS (
  SELECT s.step_reference, s.q50_days, s.q80_days,
    row_number() OVER (PARTITION BY s.step_reference ORDER BY s.scored_at, s.run_id) AS first_estimate
  FROM strata.gold.time_estimate_score AS s
  JOIN finished AS f ON f.step_reference = s.step_reference
  WHERE s.model = :model
    AND s.model_version = :champion
    AND s.as_described
    AND s.abstention IS NULL
    AND s.q50_days IS NOT NULL
    AND s.public_from >= :start
    AND s.public_from <= f.contract_signed_on
)
SELECT f.step_reference, f.first_notice_date, f.contract_signed_on, c.q50_days AS challenger_q50_days,
  c.q80_days AS challenger_q80_days, h.q50_days AS champion_q50_days, h.q80_days AS champion_q80_days, f.public_from
FROM finished AS f
JOIN challenger AS c ON c.step_reference = f.step_reference AND c.first_estimate = 1
JOIN champion AS h ON h.step_reference = f.step_reference AND h.first_estimate = 1
ORDER BY f.step_reference
