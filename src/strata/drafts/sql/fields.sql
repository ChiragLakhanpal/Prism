-- The latest value of each field a person set on the drafts in :ids (ticket 36), from the view that decides
-- "latest" once. :ids holds the draft ids joined by commas, which no draft id contains.
SELECT draft_id, row_key, field, value, set_by_id, set_by_name, set_at
FROM strata.ops.draft_fields_latest
WHERE array_contains(split(:ids, ','), draft_id)
ORDER BY draft_id, row_key, field
