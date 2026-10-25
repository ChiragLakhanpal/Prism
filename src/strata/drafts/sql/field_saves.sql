-- How many saves of its fields a draft has had (ticket 36), so the next save takes the next number.
SELECT coalesce(max(save_no), 0) AS saves
FROM strata.ops.draft_fields
WHERE draft_id = :draft_id
