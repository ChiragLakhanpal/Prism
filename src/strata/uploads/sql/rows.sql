-- An upload's activities, in the order of the officer's file. Read only after its upload's row was found.
SELECT position, activity_reference_no, description, content
FROM strata.ops.upload_rows
WHERE upload_id = :upload_id
ORDER BY position
