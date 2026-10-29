-- Saving a baseline, read back after the merge: when the save the baseline's row names was made, so a save that a
-- later one beat can take its own copied steps back (ticket 60).
SELECT saved_at
FROM strata.ops.plan_baselines
WHERE project_id = :project_id
  AND agency_id = :agency_id
