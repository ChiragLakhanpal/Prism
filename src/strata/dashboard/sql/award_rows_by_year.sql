-- Tile 4: contract-award rows per fiscal year, by the dataset they came from, from the newest snapshot
-- on or before the measure date. Each awards dataset's rows are counted as its Coverage cell in the
-- app counts them, so its years add up to that number. Fiscal 2017 to 2019 come from award notices,
-- which neither awards dataset covers. A year with no rows has no bar.
WITH chosen AS (
  SELECT measured_on, written_at
  FROM strata.ops.readiness_snapshot
  WHERE measured_on <= :measure_date
  ORDER BY measured_on DESC, written_at DESC
  LIMIT 1
)
SELECT s.fiscal_year, s.text AS fiscal_year_label, s.label AS dataset, s.count AS award_rows
FROM strata.ops.readiness_snapshot AS s
JOIN chosen AS c ON c.measured_on = s.measured_on AND c.written_at = s.written_at
WHERE s.part = 'award_year'
ORDER BY s.fiscal_year, s.position
