-- The exports of the drafts in :ids, newest first, with the evidence pack's snapshot. :ids holds the
-- draft ids joined by commas.
SELECT draft_id, export_id, exported_at, actor_id, actor_name, footnotes, sources, opened, snapshot
FROM strata.ops.draft_exports
WHERE array_contains(split(:ids, ','), draft_id)
ORDER BY exported_at DESC
