-- The latest research brief Prism wrote for a project as of a day (ticket 148): GET /api/projects/{project_id}/research
-- answers with it, so a second view calls no model.
SELECT run_id, project_id, written_at, as_of, brief
FROM strata.ops.research_briefs
WHERE project_id = :project_id
  AND as_of <= :as_of
ORDER BY written_at DESC, run_id DESC
LIMIT 1
