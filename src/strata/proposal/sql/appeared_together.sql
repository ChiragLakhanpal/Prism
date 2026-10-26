-- The contract and paragraph pairs the link scorer kept as appearing together (strata.gold.edge, ticket 22), counted
-- on the day of the pull.
SELECT count(*) AS n, CAST(NULL AS BIGINT) AS d, CAST(NULL AS STRING) AS run_id, CAST(:today AS DATE) AS measured_on
FROM strata.gold.edge
WHERE kind = 'appeared_together'
