-- The estimates loop's monthly watch (ticket 44; docs/PLAN.md section 11): one row per measure, segment and watched
-- month, written by src/strata/estimates/watch.py from the nightly job's score task. Every measure is a count with
-- its denominator, never a bare percentage (the 45 design brief). A median or a statistic is kept only from
-- estimates_loop.min_cases cases; below that, value is empty and reason is too_few_cases. Each watch appends its own
-- rows; nothing is replaced.
--
-- The measures, by name:
--   coverage            packages that finished (signed) in the coverage_window_months to month, inside the 8-in-10
--                       range Strata gave them before their first notice (count), out of those it gave one
--                       (denominator); value is empty, so no screen shows a share it did not compute
--   error_estimate      the typical error, in months, of the time estimate's middle on those packages (value)
--   error_past_range    the typical error of the past range's middle, as find_comparables gave it on each package's
--                       first notice date, on the same packages (value)
--   input_mix           for one input (segment), the chi-square statistic (value) of the champion's training mix
--                       against the packages advertised in the month (count, out of denominator training packages),
--                       with its degrees of freedom and p-value in detail
--   plan_accuracy       for one segment (anchored or other, using_strata or not_yet): plan rows with an actual
--                       signing date (count) out of the segment's rows (denominator), and the median days between
--                       planned and actual signing, early or late (value)
--   plan_duration       for one segment: rows whose package has a measurable procurement cycle time (count) and the
--                       median months from first notice to signing (value)
--   anchored_rows       plan rows dated within anchored_within_days of a date offered (count), out of plan rows
--                       published after an exposure (denominator): segment all, and published_in_month
--
-- run_id         the watch's run
-- month          the last day of the watched month
-- measure        one of the measures above
-- segment        its segment, or all
-- count          the count
-- denominator    the count it is out of
-- value          the median or statistic, when there are enough cases
-- detail         JSON: the counts behind the value
-- reason         too_few_cases or no_model when value is empty for that reason
-- measured_at    when the watch ran, in UTC
-- public_from    the day the watch ran (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.estimates_watch (
  run_id STRING NOT NULL,
  month DATE NOT NULL,
  measure STRING NOT NULL,
  segment STRING NOT NULL,
  count BIGINT,
  denominator BIGINT,
  value DOUBLE,
  detail STRING,
  reason STRING,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
