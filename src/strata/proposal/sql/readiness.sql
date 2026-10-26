-- A data readiness measure from the newest run that measured it (strata.ops.data_readiness, ticket 07): the row for
-- every subject ('all') when the run wrote one, else the sum over its subjects, such as the projects whose documents
-- the passage reader read. in_ten is the share as "about N in 10", only from data_readiness.fewest_for_a_share cases
-- and only from 1 to 9 (DESIGN.md section 7, rule 15).
WITH latest AS (
  SELECT max_by(run_id, measured_at) AS run_id, max(measured_at) AS measured_at
  FROM strata.ops.data_readiness
  WHERE source = :source AND measure = :measure
),
measured AS (
  SELECT
    CASE WHEN count_if(r.subject = 'all') > 0 THEN sum(CASE WHEN r.subject = 'all' THEN r.count END)
         ELSE sum(r.count) END AS n,
    CASE WHEN count_if(r.subject = 'all') > 0 THEN sum(CASE WHEN r.subject = 'all' THEN r.denominator END)
         ELSE sum(r.denominator) END AS d
  FROM strata.ops.data_readiness AS r
  JOIN latest AS l ON r.run_id = l.run_id
  WHERE r.source = :source AND r.measure = :measure
)
SELECT
  CAST(m.n AS BIGINT) AS n,
  CAST(m.d AS BIGINT) AS d,
  CASE WHEN m.d >= :fewest_for_a_share AND round(10.0 * m.n / m.d) BETWEEN 1 AND 9
       THEN CAST(round(10.0 * m.n / m.d) AS BIGINT) END AS in_ten,
  l.run_id,
  CAST(l.measured_at AS DATE) AS measured_on
FROM measured AS m
CROSS JOIN latest AS l
