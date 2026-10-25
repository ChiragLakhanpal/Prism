-- A viewer's latest saved language of answers and drafts (ticket 42), or no row when they never chose one.
SELECT working_language
FROM strata.ops.viewer_settings
WHERE viewer_id = :viewer_id
ORDER BY changed_at DESC
LIMIT 1
