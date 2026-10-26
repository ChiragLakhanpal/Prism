-- Tile 11: each quality check that failed in the dates chosen, newest first, with what it found in words (the 45
-- brief, section 6.3, the check phrases), from strata.ops.quality_checks (ticket 43). A task tried again counts by
-- its last try.
WITH failed AS (
  SELECT q.night, q.task_key, q.check_kind, q.table_name, q.key_name, q.found, q.expected_min, q.expected_max,
         q.checked_at
  FROM strata.ops.quality_checks AS q
  WHERE NOT q.passed AND q.night BETWEEN :date_from AND :date_to
    AND q.checked_at = (
      SELECT max(t.checked_at)
      FROM strata.ops.quality_checks AS t
      WHERE t.run_id = q.run_id AND t.task_key = q.task_key
    )
),
phrased AS (
  SELECT
    night,
    task_key,
    check_kind,
    table_name,
    checked_at,
    CASE check_kind
      WHEN 'row_count' THEN CASE WHEN found = 1 THEN :copy__dash__gov__check__row_count__one
                                 ELSE :copy__dash__gov__check__row_count__other END
      WHEN 'missing_key' THEN CASE WHEN found = 1 THEN :copy__dash__gov__check__missing_key__one
                                   ELSE :copy__dash__gov__check__missing_key__other END
      WHEN 'missing_public_from' THEN CASE WHEN found = 1 THEN :copy__dash__gov__check__missing_public_from__one
                                           ELSE :copy__dash__gov__check__missing_public_from__other END
      WHEN 'duplicates' THEN CASE WHEN found = 1 THEN :copy__dash__gov__check__duplicates__one
                                  ELSE :copy__dash__gov__check__duplicates__other END
      ELSE CASE WHEN found = 1 THEN :copy__dash__gov__check__contacts_left__one
                ELSE :copy__dash__gov__check__contacts_left__other END
    END AS template,
    found,
    expected_min,
    expected_max,
    key_name
  FROM failed
)
SELECT
  night,
  check_kind,
  found AS found_count,
  expected_min,
  expected_max,
  key_name,
  :task_label__task_key AS task,
  :check_label__check_kind AS check_name,
  table_name,
  replace(replace(replace(replace(replace(template, '{found}', format_number(found, 0)), '{table}', table_name),
                          '{min}', coalesce(format_number(expected_min, 0), '')),
                  '{max}', coalesce(format_number(expected_max, 0), '')),
          '{keyName}', coalesce(key_name, '')) AS found
FROM phrased
ORDER BY checked_at DESC, task_key, check_kind, table_name
