-- Tile 8: each source's freshness and link counts, and its status in words, in the registry's
-- order, then the pages each Procurement Plan reading route read well, from the newest snapshot on
-- or before the measure date. A known gap shows as its own row, with no link counts. The snapshot
-- writes linked and read_well as tables write them, "528 of 603". It is the table for tiles 6 and 7.
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT
  s.position,
  s.label AS source,
  s.latest_data,
  s.updates,
  s.days_late,
  CASE WHEN s.part = 'source' THEN s.text END AS linked,
  CASE WHEN s.part = 'route' THEN s.text END AS read_well,
  s.status
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part IN ('source', 'gap', 'route')
ORDER BY CASE WHEN s.part = 'route' THEN 1 ELSE 0 END, s.position
