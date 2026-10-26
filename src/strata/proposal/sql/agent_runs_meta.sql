-- The newest day an answer was written in the 90 days to the pull (strata.ops.agent_runs, ticket 13): when the KPIs
-- over answers were measured. They count many runs, so they name no one run.
SELECT CAST(NULL AS STRING) AS run_id, max(public_from) AS measured_on
FROM strata.ops.agent_runs
WHERE status = 'answered' AND public_from BETWEEN :date_from AND :date_to
