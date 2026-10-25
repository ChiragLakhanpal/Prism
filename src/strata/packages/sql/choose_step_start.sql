-- A viewer gave the date of a package's first step (ticket 27): its row in strata.app.step_start_dates is made the
-- first time and changed every time after. Nothing is deleted.
MERGE INTO strata.app.step_start_dates AS t
USING (
  SELECT
    :viewer_id AS viewer_id,
    :package_kind AS package_kind,
    :package_key AS package_key,
    CAST(:start_date AS DATE) AS start_date,
    CAST(:saved_at AS TIMESTAMP) AS saved_at
) AS s
ON t.viewer_id = s.viewer_id AND t.package_kind = s.package_kind AND t.package_key = s.package_key
WHEN MATCHED THEN UPDATE SET
  start_date = s.start_date,
  saved_at = s.saved_at
WHEN NOT MATCHED THEN INSERT
  (viewer_id, package_kind, package_key, start_date, saved_at, public_from)
  VALUES (s.viewer_id, s.package_kind, s.package_key, s.start_date, s.saved_at, CAST(s.saved_at AS DATE))
