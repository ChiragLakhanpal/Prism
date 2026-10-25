-- The drafts the refresh_drafts task looks at (strata.knowledge.lessons.notices.mark): every draft whose latest
-- state is not discarded and whose content cites a lesson version (:citation is a LIKE pattern for the table
-- name such a citation starts with). An exported draft is kept, because its page shows a notice read-only.
SELECT d.draft_id, d.content
FROM strata.ops.drafts AS d
JOIN (SELECT draft_id, max(step) AS step FROM strata.ops.draft_states GROUP BY draft_id) AS l
  ON l.draft_id = d.draft_id
JOIN strata.ops.draft_states AS s ON s.draft_id = l.draft_id AND s.step = l.step
WHERE s.state <> 'discarded'
  AND d.content LIKE :citation
ORDER BY d.created_at, d.draft_id
