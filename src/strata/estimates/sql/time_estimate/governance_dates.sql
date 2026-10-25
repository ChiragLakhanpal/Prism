-- The days on which a governance score could change, for each country and indicator: the days the
-- Indicators API published a version (strata.gold.governance_score), up to :as_of. Between two of these
-- days the score public on any day is the same, so the time estimate asks
-- src/strata/lakehouse/sql/governance_score_as_of.sql, ticket 17's one lagged join, once per day here
-- instead of once per package.
SELECT DISTINCT
  country_code,
  indicator_id,
  public_from
FROM strata.gold.governance_score
WHERE public_from <= :as_of
ORDER BY country_code, indicator_id, public_from
