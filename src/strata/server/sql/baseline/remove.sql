-- Removing a baseline: the project's baseline for this agency leaves, and no other (CLAUDE.md rule 5).
DELETE FROM strata.ops.plan_baselines
WHERE project_id = :project_id
  AND agency_id = :agency_id
