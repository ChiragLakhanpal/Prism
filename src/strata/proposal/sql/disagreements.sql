-- The disagreements found between two assertions about the same thing (strata.gold.disagreement, ticket 23),
-- counted on the day of the pull.
SELECT count(*) AS n, CAST(NULL AS BIGINT) AS d, CAST(NULL AS STRING) AS run_id, CAST(:today AS DATE) AS measured_on
FROM strata.gold.disagreement
