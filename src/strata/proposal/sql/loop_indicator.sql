-- One loop's indicator as the nightly job last wrote it for the dashboard (strata.ops.loop_indicators, ticket 45):
-- its latest value, target and comparison in the dashboard's own words, so the proposal and the dashboard agree.
SELECT
  i.latest AS text,
  i.target AS target,
  i.against AS against,
  i.run_id,
  coalesce(i.measured_on, CAST(i.written_at AS DATE)) AS measured_on
FROM strata.ops.loop_indicators AS i
WHERE i.kpi = :kpi
  AND i.written_at = (SELECT max(n.written_at) FROM strata.ops.loop_indicators AS n)
