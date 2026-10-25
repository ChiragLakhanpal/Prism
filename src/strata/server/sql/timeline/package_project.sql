-- The evidence drawer's record of a package's signing (ticket 23): the project a package belongs to, by its STEP
-- reference.
SELECT
  k.project_id
FROM strata.gold.package AS k
WHERE k.step_reference = :step_reference
