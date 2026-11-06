-- Keeping a side of a disagreement (ticket 23): the disagreement's two sides and the one Prism leans on, read as
-- the viewer, so the route accepts only one of its own sides.
SELECT
  d.disagreement_id,
  d.first_assertion_id,
  d.second_assertion_id,
  d.lean_assertion_id
FROM strata.gold.disagreement AS d
WHERE d.disagreement_id = :disagreement_id
