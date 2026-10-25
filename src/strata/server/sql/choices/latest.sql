-- The latest side a viewer kept of a disagreement for one answer or one draft (ticket 23), so the card shows it
-- again after Back. :run_id or :draft_id is the empty string when the choice is for the other kind.
SELECT
  c.choice_id,
  c.kept_assertion_id,
  c.leaned_assertion_id,
  c.reason,
  c.run_id,
  c.draft_id,
  c.made_at
FROM strata.ops.disagreement_choices AS c
WHERE c.viewer = :viewer
  AND c.disagreement_id = :disagreement_id
  AND coalesce(c.run_id, '') = :run_id
  AND coalesce(c.draft_id, '') = :draft_id
ORDER BY c.made_at DESC, c.choice_id DESC
LIMIT 1
