-- The estimates loop's watch (ticket 44): the packages that finished (signed) after :window_start and by :as_of,
-- with a procurement cycle time to measure, each with the time estimate Strata gave it as described before its first
-- notice: the champion's newest score public on or before that day (strata.gold.time_estimate_score). A package
-- Strata never scored before its notice has no range given, and rolling coverage leaves it out.
WITH finished AS (
  SELECT k.step_reference, k.first_notice_date, k.contract_signed_on, k.public_from
  FROM strata.gold.package AS k
  WHERE k.contract_signed_on > :window_start
    AND k.contract_signed_on <= :as_of
    AND k.first_notice_date IS NOT NULL
    AND k.first_notice_date <= k.contract_signed_on
),
given AS (
  SELECT s.step_reference, s.q50_days, s.q80_days, s.model_version, s.public_from,
    row_number() OVER (PARTITION BY s.step_reference ORDER BY s.scored_at DESC, s.run_id DESC) AS newest
  FROM strata.gold.time_estimate_score AS s
  JOIN finished AS f ON f.step_reference = s.step_reference
  WHERE s.as_described
    AND s.abstention IS NULL
    AND s.q80_days IS NOT NULL
    AND s.model_alias = :alias
    AND s.public_from <= f.first_notice_date
)
SELECT f.step_reference, f.first_notice_date, f.contract_signed_on, g.q50_days, g.q80_days, g.model_version,
  f.public_from
FROM finished AS f
LEFT JOIN given AS g ON g.step_reference = f.step_reference AND g.newest = 1
ORDER BY f.step_reference
