-- The latest report kept on each disagreement card under the drafts in :ids (ticket 36), from the view that
-- decides "latest" once. :ids holds the draft ids joined by commas.
SELECT draft_id, disagreement_id, kept, reason, set_by_id, set_by_name, set_at
FROM strata.ops.draft_choices_latest
WHERE array_contains(split(:ids, ','), draft_id)
ORDER BY draft_id, disagreement_id
