-- The evidence drawer's view of an agency's baseline (ticket 21), which each baseline reason cites: the
-- agency, the saved version's date and the day it was saved, once it was saved by the as-of date (ADR 0002).
-- The drawer is not told the view, so it never reads who saved it.
SELECT
  implementing_agency,
  plan_date,
  public_from
FROM strata.ops.plan_baselines
WHERE project_id = :project_id
  AND agency_id = :agency_id
  AND public_from <= :as_of
