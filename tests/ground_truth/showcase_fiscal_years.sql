-- The sample query that runs unchanged on DuckDB in the gate and on the workspace's SQL warehouse.
-- It reads no table, so both engines start from the same rows, and it uses what differs between
-- the two dialects: a VALUES list, date literals, month() and year(), datediff() and a bound
-- parameter. Run it on the warehouse with: uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
--
-- The dates are the showcase's (P130164), each recorded with its quote and its test in
-- tests/ground_truth/values.toml: mid-term-review (May 16, 2016), isr-7-date (August 26, 2016),
-- restructuring (July 27, 2017), isr-12-date (April 10, 2018) and icr-date (October 10, 2019). Fiscal years run July to June, so a date from July on
-- falls in the next year's FY. The day counts to the ICR were computed once with Python's datetime.
-- The as-of date drops the ICR, which became public after it.
-- param: as_of = 2018-12-31
-- expect: event,happened_on,fiscal_year,days_before_icr
-- expect: Mid-term review,2016-05-16,2016,1242
-- expect: ISR 7,2016-08-26,2017,1140
-- expect: Restructuring,2017-07-27,2018,805
-- expect: ISR 12,2018-04-10,2018,548
SELECT
  event,
  happened_on,
  CASE WHEN month(happened_on) >= 7 THEN year(happened_on) + 1 ELSE year(happened_on) END AS fiscal_year,
  datediff(DATE '2019-10-10', happened_on) AS days_before_icr
FROM VALUES
  ('ISR 7', DATE '2016-08-26'),
  ('Mid-term review', DATE '2016-05-16'),
  ('ICR', DATE '2019-10-10'),
  ('Restructuring', DATE '2017-07-27'),
  ('ISR 12', DATE '2018-04-10') AS showcase(event, happened_on)
WHERE happened_on <= CAST(:as_of AS DATE)
ORDER BY happened_on
