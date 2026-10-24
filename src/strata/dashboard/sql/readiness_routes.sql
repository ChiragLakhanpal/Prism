-- Tile 7: the share of Procurement Plan pages each reading route read well, for each route with
-- enough pages to give a percentage (config/thresholds.toml, data_readiness.fewest_for_a_percentage),
-- as tile 6 does for links.
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT s.position, s.label AS route, s.share_percent, s.count, s.denominator
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part = 'route' AND s.share_percent IS NOT NULL
ORDER BY s.position
