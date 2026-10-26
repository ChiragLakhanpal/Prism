-- One upload by its id, whatever its team: the route asks the access rule before it shows any of it.
SELECT upload_id, team_key, uploader_id, uploader_name, project_id, implementing_agency, file_name, reading, uploaded_at
FROM strata.ops.uploads
WHERE upload_id = :upload_id
