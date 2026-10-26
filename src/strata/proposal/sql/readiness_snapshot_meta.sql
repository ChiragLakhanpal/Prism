-- When the Data readiness page's snapshot that tile 4 and Figure 2 read was measured, and its run: the newest on or
-- before the pull's day (strata.ops.readiness_snapshot, ticket 16).
SELECT max_by(run_id, written_at) AS run_id, max(measured_on) AS measured_on
FROM strata.ops.readiness_snapshot
WHERE measured_on <= :measure_date
