-- find_comparables: a comparable's project name, for the evidence drawer's meta line.
SELECT project_name
FROM strata.gold.project
WHERE project_id = :project_id
