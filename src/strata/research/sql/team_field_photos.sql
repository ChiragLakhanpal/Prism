-- A project's field photos kept under a team, and every one of the viewer's own whatever team they were on (an
-- uploader always sees their own), newest first (ticket 150): the Deep research tab's list, the count its limit
-- reads, and the items research_evidence adds for the viewer's team.
SELECT photo_id, project_id, team_key, uploader_id, uploader_name, file_name, caption, taken_on, latitude, longitude,
       place, geo_loc_id, stored_as, media_type, uploaded_at
FROM strata.ops.field_photos
WHERE project_id = :project_id
  AND (team_key = :team_key OR uploader_id = :uploader_id)
ORDER BY uploaded_at DESC, photo_id
