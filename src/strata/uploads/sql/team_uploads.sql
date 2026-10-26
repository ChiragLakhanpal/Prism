-- Every upload kept under a team, and every upload of the viewer's own whatever team they were on (an uploader
-- always sees their own), newest first, for the Packages tab and the count on Check my plan.
SELECT upload_id, team_key, uploader_id, uploader_name, project_id, implementing_agency, file_name, reading, uploaded_at
FROM strata.ops.uploads
WHERE team_key = :team_key
   OR uploader_id = :uploader_id
ORDER BY uploaded_at DESC, upload_id
