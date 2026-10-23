-- strata.gold.governance_score: each version of each CPIA and WGI score. A version starts on the
-- public_from of the first page that gave the value, and a later page with a different value for the
-- same country, indicator and year starts the next one. Years with no value are left out.
-- key: country_code, indicator_id, year, public_from
WITH scores AS (
  SELECT DISTINCT country_code, country_iso3, indicator_id, indicator_name, year, value, public_from
  FROM strata.silver.indicators
  WHERE value IS NOT NULL AND year IS NOT NULL AND country_code IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY country_code, indicator_id, year, public_from ORDER BY value) = 1
),
ordered AS (
  SELECT
    *,
    lag(value) OVER (PARTITION BY country_code, indicator_id, year ORDER BY public_from) AS earlier_value
  FROM scores
),
versions AS (
  SELECT *
  FROM ordered
  WHERE earlier_value IS NULL OR earlier_value <> value
)
SELECT
  country_code,
  country_iso3,
  indicator_id,
  indicator_name,
  year,
  value,
  lead(public_from) OVER (PARTITION BY country_code, indicator_id, year ORDER BY public_from) AS superseded_on,
  public_from
FROM versions
