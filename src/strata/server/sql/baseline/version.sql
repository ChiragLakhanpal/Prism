-- Saving a baseline (ticket 21): the agency's versions of the project's plans on the date asked, public
-- by the day of saving, with how many activities the layout parser read in each. Only a version with
-- activities can be a baseline, since a baseline is its planned dates.
SELECT
  v.document_id,
  v.implementing_agency,
  v.plan_date,
  v.public_from,
  (SELECT count(*) FROM strata.silver.plan_rows AS r WHERE r.document_id = v.document_id) AS activities
FROM strata.silver.plan_versions AS v
WHERE v.project_id = :project_id
  AND v.plan_date = :plan_date
  AND v.public_from <= :today
ORDER BY v.public_from, v.document_id
