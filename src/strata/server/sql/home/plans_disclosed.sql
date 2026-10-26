-- The Procurement Plan versions disclosed in Home's window (ticket 41; the 41 design brief, section 4.1): every
-- version whose Disclosed date (public_from) falls from :start to :end, newest first. Home keeps those of the
-- projects the viewer follows and checks each one with check_plan.
SELECT
  v.project_id,
  v.implementing_agency,
  v.plan_date,
  v.public_from,
  v.document_id
FROM strata.silver.plan_versions AS v
WHERE v.public_from >= :start
  AND v.public_from <= :end
ORDER BY v.public_from DESC, v.project_id, v.implementing_agency, v.plan_date DESC
