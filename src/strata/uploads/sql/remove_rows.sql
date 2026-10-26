-- The activities a failed save wrote before its upload's row, which no read returns: removed by the upload they
-- name, so nothing of a failed upload stays (CLAUDE.md rule 5: a DELETE with a WHERE).
DELETE FROM strata.ops.upload_rows
WHERE upload_id = :upload_id
