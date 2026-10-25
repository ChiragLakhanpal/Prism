-- One row for each activity of an upload in strata.ops.uploads (ticket 38), in the order of the officer's file.
-- Written before the upload's own row, so a reader that finds the upload finds every one of its rows; a write
-- that fails part way leaves rows no upload names, which no read returns and which the store then removes with a
-- DELETE that names the upload. Official Use Only, like the upload: the deploy masks every column that holds the
-- officer's words.
--
-- upload_id              the upload it belongs to
-- position               its place in the file, from 1
-- activity_reference_no  its Activity Reference No., or NULL when the file gives none yet
-- description            its Description, as the file gives it
-- content                its STEP values, each step's Planned and Actual dates, its section and its data notes,
--                        as JSON
-- public_from            the day the upload was kept, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.upload_rows (
  upload_id STRING NOT NULL,
  position INT NOT NULL,
  activity_reference_no STRING,
  description STRING,
  content STRING NOT NULL,
  public_from DATE NOT NULL
)
