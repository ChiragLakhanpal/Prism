-- The estimates loop (ticket 44): each project's region, as strata.gold.project writes it, for the re-check a new
-- edition starts on a lesson: the region's reviewers act on it, as on any re-check (ticket 29).
SELECT p.project_id, p.region, p.public_from
FROM strata.gold.project AS p
WHERE p.region IS NOT NULL
ORDER BY p.project_id
