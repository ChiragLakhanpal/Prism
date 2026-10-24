-- Every note the lesson review writer wrote, oldest first within each item, so the last is the newest.
SELECT
  n.item_id,
  n.written_at,
  n.status,
  n.content,
  n.library_versions,
  n.agent,
  n.agent_version,
  n.error
FROM strata.ops.lesson_review_notes AS n
ORDER BY n.item_id, n.written_at
