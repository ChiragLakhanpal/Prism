-- One draft by its id, whatever its team: the route asks the access rule before it shows any of it.
SELECT draft_id, kind, team_key, author_id, author_name, project_id, subject, content, created_at
FROM strata.ops.drafts
WHERE draft_id = :draft_id
