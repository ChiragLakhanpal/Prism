-- Tile 5: every charted source's rows per fiscal year, with exact counts, from the newest snapshot on
-- or before the measure date: the table beside tile 4's chart, and the coverage of the sources that
-- are not awards. Each source's rows are counted as its Coverage cell in the app counts them, so its
-- years add up to that number on the same date.
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT s.position, s.label AS source, s.fiscal_year, s.text AS fiscal_year_label, s.count AS source_rows
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part IN ('award_year', 'source_year')
ORDER BY s.position, s.fiscal_year
