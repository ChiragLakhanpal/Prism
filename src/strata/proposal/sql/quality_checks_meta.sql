-- When the newest contacts_left check ran, and its run (strata.ops.quality_checks, ticket 43): the check the KPI
-- contacts_left reads.
SELECT max_by(run_id, checked_at) AS run_id, CAST(max(checked_at) AS DATE) AS measured_on
FROM strata.ops.quality_checks
WHERE check_kind = 'contacts_left' AND night BETWEEN :date_from AND :date_to
