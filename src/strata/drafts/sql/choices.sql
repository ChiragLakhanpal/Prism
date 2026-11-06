-- The latest report each person kept on each disagreement card under the drafts in :ids (ticket 36), from ticket
-- 23's strata.ops.disagreement_choices, where the card's keep action records it with the draft's id. The store keeps
-- only the author's: a teammate's choice does not resolve a card on someone else's draft. Going back to Prism's
-- choice is a row whose kept side is the leaned one. :ids holds the draft ids joined by commas.
SELECT
  c.draft_id,
  c.disagreement_id,
  c.viewer,
  c.kept_assertion_id,
  c.leaned_assertion_id,
  c.reason,
  c.made_at
FROM strata.ops.disagreement_choices AS c
WHERE array_contains(split(:ids, ','), c.draft_id)
QUALIFY row_number() OVER (
  PARTITION BY c.draft_id, c.disagreement_id, c.viewer
  ORDER BY c.made_at DESC, c.choice_id DESC
) = 1
ORDER BY c.draft_id, c.disagreement_id
