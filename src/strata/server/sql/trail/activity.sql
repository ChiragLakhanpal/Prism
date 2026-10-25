-- The contract trail (ticket 22): which project holds a STEP reference, from every record that carries it (its
-- package, its plan rows, its notices and its contracts), whatever the as-of date, so an activity opened under
-- the wrong project finds its own, and an activity whose records became public later is still known. The
-- project with the most records wins, then the earliest public one.
WITH held AS (
  SELECT project_id, public_from FROM strata.gold.package WHERE step_reference = :reference
  UNION ALL
  SELECT project_id, public_from FROM strata.silver.plan_rows WHERE activity_reference_no = :reference
  UNION ALL
  SELECT project_id, public_from FROM strata.gold.notice WHERE step_reference = :reference
  UNION ALL
  SELECT project_id, public_from FROM strata.gold.contract WHERE step_reference = :reference
)
SELECT
  h.project_id,
  p.project_name,
  min(h.public_from) AS first_public
FROM held AS h
LEFT JOIN strata.gold.project AS p ON p.project_id = h.project_id
WHERE h.project_id IS NOT NULL
GROUP BY h.project_id, p.project_name
ORDER BY count(*) DESC, min(h.public_from), h.project_id
LIMIT 1
