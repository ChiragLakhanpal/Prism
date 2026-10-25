-- Following (ticket 37): the projects one viewer follows now, each with when they last followed it. A project
-- is followed while its latest row in strata.ops.follows says so.
SELECT
  f.project_id,
  f.changed_at
FROM strata.ops.follows AS f
WHERE f.viewer_id = :viewer_id
  AND f.following
  AND NOT EXISTS (
    SELECT 1 FROM strata.ops.follows AS later
    WHERE later.viewer_id = f.viewer_id
      AND later.project_id = f.project_id
      AND later.changed_at > f.changed_at
  )
ORDER BY f.project_id
