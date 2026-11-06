-- One row for each field photo a World Bank staff member added to a project's Deep research tab (ticket 150). A field
-- photo is Official Use Only: the app writes it as its own service principal, and every read goes through the one
-- access rule in src/strata/server/access.py, which shows a photo only to its uploader and the team they were on.
-- The file itself is kept in the volume strata.ops.field_photos on the workspace, and in a folder beside the local
-- DuckDB file on this computer, never in the repo; stored_as names it there. The file is written first and this row
-- last, so a row a reader finds always has its file. Nothing here reaches the search index, a metric view or the
-- dashboard. Nothing deletes a photo.
--
-- photo_id       the photo's id, in its address: fph- and twelve hex digits
-- project_id     the project the photo belongs to, such as P156634
-- team_key       the uploader's team when it was added: team:<key> from config/roles.toml, or viewer:<user id>
-- uploader_id    the user id the Databricks App forwarded for the uploader
-- uploader_name  the uploader's name as the App forwarded it
-- file_name      the file's name as the browser sent it
-- caption        what the uploader wrote about the photo; the brief describes the photo only in these words
-- taken_on       the day the camera recorded in the photo's EXIF data, or empty when it recorded none
-- latitude       the position the camera recorded in the photo's EXIF data, in degrees, or empty
-- longitude
-- place          the project location nearest that position (the project's geo_locations), or empty
-- geo_loc_id     that location's id in the project's record, or empty
-- stored_as      the file's name in the photo store's folder or volume
-- media_type     image/jpeg or image/png
-- uploaded_at    when it was kept, in UTC
-- public_from    the day it was kept, in UTC (ADR 0002). The photo is never public: only its team reads it.
CREATE TABLE IF NOT EXISTS strata.ops.field_photos (
  photo_id STRING NOT NULL,
  project_id STRING NOT NULL,
  team_key STRING NOT NULL,
  uploader_id STRING NOT NULL,
  uploader_name STRING,
  file_name STRING NOT NULL,
  caption STRING NOT NULL,
  taken_on DATE,
  latitude DOUBLE,
  longitude DOUBLE,
  place STRING,
  geo_loc_id STRING,
  stored_as STRING NOT NULL,
  media_type STRING NOT NULL,
  uploaded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
