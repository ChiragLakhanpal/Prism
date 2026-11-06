-- How many implementing agencies of a project published a Procurement Plan that Prism read and that was public by
-- the as-of date (ADR 0002), for the Project Paper summary's scope caption: a summary covers one agency's plan, and
-- the caption says when the project has others (ticket 36). Run as the viewer.
SELECT count(DISTINCT implementing_agency) AS agencies
FROM strata.silver.plan_versions
WHERE project_id = :project_id
  AND implementing_agency IS NOT NULL
  AND public_from <= :as_of
