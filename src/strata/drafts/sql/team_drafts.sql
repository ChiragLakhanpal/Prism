-- Every draft saved by a team, and every draft of the viewer's own whatever team they were on when they
-- saved it (an author always sees their own drafts), for the Drafts tab and for the notice on Check a
-- plan that names a draft someone on the team already started on the same plan.
SELECT draft_id, kind, team_key, author_id, author_name, project_id, subject, content, created_at
FROM strata.ops.drafts
WHERE team_key = :team_key
   OR author_id = :author_id
ORDER BY created_at, draft_id
