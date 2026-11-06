-- KPI rolling_coverage (config/kpis.toml), the estimates loop's leading indicator: of the packages that finished
-- (signed) in the 12 months to each watched month, how many finished inside the 8-in-10 range Prism gave them before
-- their first notice, as the monthly watch stored them (strata.ops.estimates_watch, coverage, segment all, each month
-- from its newest watch; ticket 44). coverage_percent is a whole percent only from
-- data_readiness.fewest_for_a_percentage packages (DESIGN.md section 7, rule 15), so the chart has no point below
-- it, and coverage_cell writes the counts with their share as a table does. The target edges are
-- time_estimate.coverage_low and coverage_high. Newest first, in the dates chosen.
WITH months AS (
  SELECT w.month, w.count AS inside, w.denominator AS finished
  FROM strata.ops.estimates_watch AS w
  WHERE w.measure = 'coverage' AND w.segment = 'all' AND w.month BETWEEN :date_from AND :date_to
    AND w.measured_at = (
      SELECT max(n.measured_at)
      FROM strata.ops.estimates_watch AS n
      WHERE n.measure = 'coverage' AND n.segment = 'all' AND n.month = w.month
    )
)
SELECT
  month,
  finished,
  inside,
  inside AS numerator,
  finished AS denominator,
  :percent__inside__finished AS coverage_percent,
  :ratio__inside__finished AS coverage_cell,
  CAST(round(100 * :threshold__time_estimate__coverage_low) AS BIGINT) AS target_low,
  CAST(round(100 * :threshold__time_estimate__coverage_high) AS BIGINT) AS target_high
FROM months
ORDER BY month DESC
