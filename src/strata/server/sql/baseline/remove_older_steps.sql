-- Saving a baseline, last: the copied planned dates of earlier saves leave, only this project's and
-- agency's (CLAUDE.md rule 5), once the baseline's row names the new save.
DELETE FROM strata.ops.plan_baseline_steps
WHERE project_id = :project_id
  AND agency_id = :agency_id
  AND saved_at < CAST(:saved_at AS TIMESTAMP)
