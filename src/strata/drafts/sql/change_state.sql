-- A person moves a draft to its next state: one new row after the latest, written only while the latest
-- state is still the one they saw (:expected), so a change made in another tab or window is never
-- written over. It is a MERGE on (draft_id, step), so when two acts arrive at the same moment, Delta's
-- conflict check refuses the second writer instead of keeping two rows for one step. Nothing is updated
-- or deleted; the history keeps every step.
MERGE INTO strata.ops.draft_states AS t
USING (
  SELECT
    s.draft_id,
    s.step + 1 AS step,
    :state AS state,
    s.state AS from_state,
    :actor_id AS actor_id,
    :actor_name AS actor_name,
    CAST(:changed_at AS TIMESTAMP) AS changed_at,
    CAST(:changed_at AS DATE) AS public_from
  FROM strata.ops.draft_states AS s
  WHERE s.draft_id = :draft_id
    AND s.state = :expected
    AND s.step = (
      SELECT max(latest.step)
      FROM strata.ops.draft_states AS latest
      WHERE latest.draft_id = :draft_id
    )
) AS n
ON t.draft_id = n.draft_id AND t.step = n.step
WHEN NOT MATCHED THEN
  INSERT (draft_id, step, state, from_state, actor_id, actor_name, changed_at, public_from)
  VALUES (n.draft_id, n.step, n.state, n.from_state, n.actor_id, n.actor_name, n.changed_at, n.public_from)
