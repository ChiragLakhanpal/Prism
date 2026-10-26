-- KPI contacts_left (config/kpis.toml): the notices in which the latest check in the dates chosen found an email
-- address or a labelled phone number that ingestion missed (ticket 43's contacts_left check, which reads
-- strata.lakehouse.contacts' own patterns), out of the rows of the notices table that check read, from the row count
-- check of the same try. Always one row: "None yet" before the first check.
WITH latest AS (
  SELECT run_id, checked_at
  FROM strata.ops.quality_checks
  WHERE check_kind = 'contacts_left' AND night BETWEEN :date_from AND :date_to
  ORDER BY checked_at DESC
  LIMIT 1
),
found AS (
  SELECT sum(c.found) AS notices_left, sum(r.found) AS notices
  FROM strata.ops.quality_checks AS c
  JOIN latest AS l ON c.run_id = l.run_id AND c.checked_at = l.checked_at
  LEFT JOIN strata.ops.quality_checks AS r
    ON r.run_id = c.run_id AND r.checked_at = c.checked_at AND r.table_name = c.table_name
   AND r.check_kind = 'row_count'
  WHERE c.check_kind = 'contacts_left'
)
SELECT
  notices_left AS numerator,
  notices AS denominator,
  notices_left AS value,
  CASE
    WHEN notices IS NULL OR notices = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(notices_left, 0)), '{d}',
                 format_number(notices, 0))
  END AS display
FROM found
