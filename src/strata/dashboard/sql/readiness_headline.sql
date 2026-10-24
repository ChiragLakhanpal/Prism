-- Tile 3: the day's headline, from the newest snapshot of the Data readiness page on or before the
-- dashboard's measure date (strata.ops.readiness_snapshot).
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT s.measured_on, s.text AS headline
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part = 'headline'
