-- The hindsight test (ticket 34): every project exposed to Strata by :as_of, with the first day it was, which the
-- gate set leaves out and lists. The exposure log, strata.ops.exposures (ticket 44), is the one place an exposure is
-- defined and written: a past range or a time estimate the server showed for one of the project's packages in the
-- World Bank staff view. The recall KPI is the stored hindsight recall of a run over this gate set, so it leaves
-- out the same projects.
SELECT
  e.project_id,
  min(e.exposed_on) AS first_exposed_on,
  min(e.public_from) AS public_from
FROM strata.ops.exposures AS e
WHERE e.public_from <= :as_of
  AND e.project_id IS NOT NULL
GROUP BY e.project_id
ORDER BY e.project_id
