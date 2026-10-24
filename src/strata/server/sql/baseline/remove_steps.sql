-- Saving or removing a baseline: its copied planned dates leave first, only this project's and agency's
-- (CLAUDE.md rule 5).
DELETE FROM strata.ops.plan_baseline_steps
WHERE project_id = :project_id
  AND agency_id = :agency_id
