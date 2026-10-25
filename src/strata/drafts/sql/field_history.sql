-- Every save of a draft's fields, oldest first (ticket 36), for the evidence pack's "Fields you set" table,
-- which records who set each owner and rating, and when.
SELECT draft_id, save_no, row_key, field, value, set_by_id, set_by_name, set_at
FROM strata.ops.draft_fields
WHERE draft_id = :draft_id
ORDER BY save_no
