-- The governance score that was public on a date (ADR 0002): for one country and indicator, the
-- latest year that had a version public on :as_of, at the version current then. A version counts
-- from the day the Indicators API published it until the day it published the next one, so a join
-- on a date between two versions takes the earlier value, and a year's score counts only once the
-- API had published it, which lags the year it describes. This is the one definition of the join;
-- tools and models that take a governance score as of a date run it.
SELECT
  country_code,
  indicator_id,
  year,
  value,
  public_from,
  superseded_on
FROM strata.gold.governance_score
WHERE country_code = :country_code
  AND indicator_id = :indicator_id
  AND public_from <= CAST(:as_of AS DATE)
  AND (superseded_on IS NULL OR superseded_on > CAST(:as_of AS DATE))
ORDER BY year DESC
LIMIT 1
