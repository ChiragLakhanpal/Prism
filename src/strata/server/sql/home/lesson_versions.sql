-- The example lesson versions only one viewer sees (ticket 41), in order.
SELECT lesson_id, version, version_row
FROM strata.ops.example_lesson_versions
WHERE viewer_id = :viewer_id
ORDER BY lesson_id, version
