-- A person moves a draft to its next state: one new row after the latest, written only while the latest
-- state is still the one they saw (:expected), so a change made in another tab or window is never
-- written over. Nothing is updated or deleted; the history keeps every step.
INSERT INTO strata.ops.draft_states (draft_id, step, state, from_state, actor_id, actor_name, changed_at, public_from)
SELECT
  s.draft_id,
  s.step + 1,
  :state,
  s.state,
  :actor_id,
  :actor_name,
  CAST(:changed_at AS TIMESTAMP),
  CAST(:changed_at AS DATE)
FROM strata.ops.draft_states AS s
WHERE s.draft_id = :draft_id
  AND s.state = :expected
  AND s.step = (
    SELECT max(latest.step)
    FROM strata.ops.draft_states AS latest
    WHERE latest.draft_id = :draft_id
  )
