-- The latest row of each source, subject and measure in strata.ops.data_readiness that was public
-- on or before the as-of date (ADR 0002). The newest measured_at picks the run, because as_of is set
-- only on the freshness measures. The page never sums or averages one measure over runs.
SELECT
  source,
  subject,
  measure,
  kind,
  count,
  denominator,
  as_of,
  CAST(measured_at AS DATE) AS measured_on,
  run_id,
  public_from
FROM strata.ops.data_readiness
WHERE public_from <= :as_of
QUALIFY row_number() OVER (PARTITION BY source, subject, measure ORDER BY measured_at DESC, run_id DESC) = 1
