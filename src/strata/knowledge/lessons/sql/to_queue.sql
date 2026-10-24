-- The passing proposals of one project, with the project's region, which the review queue sorts by.
SELECT
  l.proposal_id,
  l.project_id,
  pr.region
FROM strata.silver.lesson_proposals AS l
LEFT JOIN strata.gold.project AS pr ON pr.project_id = l.project_id
WHERE l.project_id = :project_id
  AND l.quote_check = 'passed'
ORDER BY l.proposal_id
