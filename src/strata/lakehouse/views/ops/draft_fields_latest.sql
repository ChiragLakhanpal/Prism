-- The latest value of each field a person set on a draft (ticket 36): the newest save of each draft, row and field
-- in strata.ops.draft_fields, whose rows are only ever appended. A value that is empty was removed. The draft
-- routes, the holds and the Word file read this view, so "latest" is decided once.
CREATE OR REPLACE VIEW strata.ops.draft_fields_latest AS
SELECT f.*
FROM strata.ops.draft_fields AS f
QUALIFY row_number() OVER (PARTITION BY f.draft_id, f.row_key, f.field ORDER BY f.save_no DESC, f.set_at DESC) = 1
