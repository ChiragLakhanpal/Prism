-- Every version of every lesson, with what each decision changed, for the version notices
-- (strata.knowledge.lessons.notices.mark).
SELECT lesson_id, version, state, change_kind, decided_on
FROM strata.ops.lesson_versions
ORDER BY lesson_id, version
