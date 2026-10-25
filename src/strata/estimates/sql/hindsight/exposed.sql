-- The hindsight test (ticket 34): every project exposed to Strata by :as_of, with the first day it was, which the
-- gate set leaves out and lists. This is the one place the test reads exposures from; ticket 44 can point it at its
-- exposure log. strata.ops.exposed_projects says what counts as an exposure.
SELECT
  e.project_id,
  min(e.exposed_on) AS first_exposed_on,
  min(e.public_from) AS public_from
FROM strata.ops.exposed_projects AS e
WHERE e.public_from <= :as_of
GROUP BY e.project_id
ORDER BY e.project_id
