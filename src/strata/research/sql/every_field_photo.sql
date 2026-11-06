-- Every team's field photos, newest first (ticket 160): the App loads their files into the photo route's memory when it
-- starts. The route still asks the access rule on every request before it serves a photo's bytes.
SELECT photo_id, project_id, team_key, uploader_id, uploader_name, file_name, caption, taken_on, latitude, longitude,
       place, geo_loc_id, stored_as, media_type, uploaded_at
FROM strata.ops.field_photos
ORDER BY uploaded_at DESC, photo_id
