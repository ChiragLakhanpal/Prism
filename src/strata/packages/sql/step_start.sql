-- The date of a package's first step a viewer gave, if any (ticket 27).
SELECT d.start_date, d.saved_at
FROM strata.app.step_start_dates AS d
WHERE d.viewer_id = :viewer_id
  AND d.package_kind = :package_kind
  AND d.package_key = :package_key
