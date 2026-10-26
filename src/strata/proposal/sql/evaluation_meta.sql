-- When the newest run of one scorer ran, and its run id (strata.ops.evaluation_result): the run a KPI's own query
-- reads its numbers from.
SELECT max_by(run_id, ran_at) AS run_id, CAST(max(ran_at) AS DATE) AS measured_on
FROM strata.ops.evaluation_result
WHERE scorer = :scorer AND public_from BETWEEN :date_from AND :date_to
