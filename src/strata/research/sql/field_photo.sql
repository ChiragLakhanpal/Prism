-- One field photo by its id, whatever its team (ticket 150): the route asks the access rule before it shows any of it.
SELECT photo_id, project_id, team_key, uploader_id, uploader_name, file_name, caption, taken_on, latitude, longitude,
       place, geo_loc_id, stored_as, media_type, uploaded_at
FROM strata.ops.field_photos
WHERE photo_id = :photo_id
