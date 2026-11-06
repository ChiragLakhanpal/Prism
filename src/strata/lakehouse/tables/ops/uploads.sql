-- One row for each Procurement Plan an implementing agency team uploaded and Prism read and checked (ticket 38).
-- An upload is Official Use Only: the app writes it as its own service principal, only after the file was read
-- and checked, and every read goes through the one access rule in src/strata/server/access.py, which shows an
-- upload only to its uploader and the team they were on. The file itself is never kept: its activities are in
-- strata.ops.upload_rows, written first, so an upload a reader can find always has all of its rows. Nothing here
-- reaches the search index, a metric view or the dashboard, and the deploy masks the columns that hold the
-- officer's words (strata.lakehouse.masks), so a SQL editor reads them as NULL. Nothing deletes an upload.
--
-- Uploads render as they are today, so no read filters them by public_from.
--
-- upload_id        the upload's id, in its address
-- team_key         the uploader's team when it was uploaded: team:<key> from config/roles.toml
-- uploader_id      the user id the Databricks App forwarded for the uploader
-- uploader_name    the uploader's name as the App forwarded it, which teammates read on the page
-- idempotency_key  the key the browser sent, so a second request with the same key keeps nothing new
-- project_id       the project the plan belongs to
-- implementing_agency  the agency the team's roles entry names, as the project's record names it
-- file_name        the file's name as the browser sent it
-- reading          how the file was read, as JSON: the sheets, the headers used and not used, and the activities
-- uploaded_at      when it was kept, in UTC
-- public_from      the day it was kept, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.uploads (
  upload_id STRING NOT NULL,
  team_key STRING NOT NULL,
  uploader_id STRING NOT NULL,
  uploader_name STRING,
  idempotency_key STRING,
  project_id STRING NOT NULL,
  implementing_agency STRING NOT NULL,
  file_name STRING NOT NULL,
  reading STRING NOT NULL,
  uploaded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
