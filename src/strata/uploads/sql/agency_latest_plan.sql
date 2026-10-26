-- An implementing agency's latest Procurement Plan for one project, public by the as-of date (ticket 38), which Check
-- my plan offers beside the upload.
SELECT v.implementing_agency, v.plan_date, v.disclosed_on
FROM strata.silver.plan_versions AS v
WHERE v.project_id = :project_id
  AND lower(v.implementing_agency) = lower(:agency)
  AND v.public_from <= :as_of
ORDER BY v.plan_date DESC, v.public_from DESC
LIMIT 1
