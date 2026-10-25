-- The version notices already set, so a second night adds none of them again.
SELECT draft_id, row_key, lesson_id, cited_version, current_version
FROM strata.ops.lesson_version_notices
