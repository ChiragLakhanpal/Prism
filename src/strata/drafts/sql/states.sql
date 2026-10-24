-- Every state the drafts in :ids have been in, in order. :ids holds the draft ids joined by commas, which
-- no draft id contains.
SELECT draft_id, step, state, from_state, actor_id, actor_name, changed_at
FROM strata.ops.draft_states
WHERE array_contains(split(:ids, ','), draft_id)
ORDER BY draft_id, step
