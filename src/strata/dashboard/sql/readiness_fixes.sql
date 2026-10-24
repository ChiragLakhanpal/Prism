-- Tile 9: the fixes, ranked by the projects each would add evidence to, as the app ranks them.
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT s.position AS rank, s.text AS fix, s.projects
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part = 'fix'
ORDER BY s.position
