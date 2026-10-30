-- Saving a baseline, after the earlier saves' steps leave: when a later save beat this one, so the baseline's row
-- names a later save, this save's own copied planned dates leave at once, only this project's and agency's and only
-- this save's (CLAUDE.md rule 5; ticket 60). The comparison runs here, where every engine reads saved_at the same way.
DELETE FROM strata.ops.plan_baseline_steps
WHERE project_id = :project_id
  AND agency_id = :agency_id
  AND saved_at = CAST(:saved_at AS TIMESTAMP)
  AND EXISTS (
    SELECT 1
    FROM strata.ops.plan_baselines AS b
    WHERE b.project_id = :project_id
      AND b.agency_id = :agency_id
      AND b.saved_at > CAST(:saved_at AS TIMESTAMP)
  )
