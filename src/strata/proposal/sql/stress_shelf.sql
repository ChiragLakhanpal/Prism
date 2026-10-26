-- The shelf of the hardest documents in the slice (strata.ops.stress_shelf, ticket 18), from its newest run: the
-- documents the reader read, out of the shelf's documents.
WITH latest AS (
  SELECT max_by(run_id, measured_at) AS run_id, max(measured_at) AS measured_at
  FROM strata.ops.stress_shelf
)
SELECT
  CAST(count_if(s.state = 'read') AS BIGINT) AS n,
  CAST(count(*) AS BIGINT) AS d,
  CAST(NULL AS BIGINT) AS in_ten,
  max(l.run_id) AS run_id,
  CAST(max(l.measured_at) AS DATE) AS measured_on
FROM strata.ops.stress_shelf AS s
JOIN latest AS l ON s.run_id = l.run_id
