-- Saving a baseline that a later save beat: this save's own copied planned dates leave at once, only this project's
-- and agency's and only this save's (CLAUDE.md rule 5), since the baseline's row names the later save (ticket 60).
DELETE FROM strata.ops.plan_baseline_steps
WHERE project_id = :project_id
  AND agency_id = :agency_id
  AND saved_at = CAST(:saved_at AS TIMESTAMP)
