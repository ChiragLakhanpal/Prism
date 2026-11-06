-- The latest research brief Prism wrote for a project as of a day (ticket 148): GET /api/projects/{project_id}/research
-- answers with it, so a second view calls no model. A brief written from a team's field photos (ticket 150) is read
-- only by that team: the viewer's team_key, or the empty key of a viewer on no team, which matches no brief.
SELECT run_id, project_id, written_at, as_of, brief
FROM strata.ops.research_briefs
WHERE project_id = :project_id
  AND as_of <= :as_of
  AND (team_key IS NULL OR team_key = :team_key)
ORDER BY written_at DESC, run_id DESC
LIMIT 1
