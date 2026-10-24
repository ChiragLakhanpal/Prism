-- Tile 6: the share of rows that link, for each linked measure with enough rows to give a percentage
-- (config/thresholds.toml, data_readiness.fewest_for_a_percentage). The table in tile 8 keeps every
-- link's counts.
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT s.position, s.label AS link, s.share_percent, s.count, s.denominator
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part = 'link' AND s.share_percent IS NOT NULL
ORDER BY s.position
