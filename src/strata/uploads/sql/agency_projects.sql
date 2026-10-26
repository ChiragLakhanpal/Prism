-- The projects whose records may name an implementing agency, newest first (ticket 38): the route keeps those whose
-- record lists the agency by name, split as the projects API joins its agencies (check_plan.implementing_agencies).
SELECT p.project_id, p.project_name, p.implementing_agency
FROM strata.gold.project AS p
WHERE p.public_from <= :as_of
  AND lower(p.implementing_agency) LIKE '%' || lower(:agency) || '%'
ORDER BY p.public_from DESC, p.project_id
