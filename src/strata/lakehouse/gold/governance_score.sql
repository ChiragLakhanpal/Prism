-- strata.gold.governance_score: each version of each CPIA and WGI score. A version starts on the
-- public_from of the first page that gave the value, and a later page with a different value for the
-- same country, indicator and year starts the next one. Pages are taken in the order Strata fetched
-- them. Years with no value are left out. A page that changes a value but keeps the lastupdated date
-- of the page before it cannot say when the new value came out, so that version starts on the day
-- Strata first fetched it, never earlier, and the earlier value stays until then (ticket 63; ticket
-- 17's verify, F2). A revision with a later lastupdated date starts on that date (ADR 0002).
-- key: country_code, indicator_id, year, public_from
WITH scores AS (
  SELECT country_code, country_iso3, indicator_id, indicator_name, year, value, public_from, fetched_at, page_hash
  FROM strata.silver.indicators
  WHERE value IS NOT NULL AND year IS NOT NULL AND country_code IS NOT NULL
),
ordered AS (
  SELECT
    *,
    lag(value) OVER (PARTITION BY country_code, indicator_id, year ORDER BY fetched_at, page_hash) AS earlier_value,
    lag(public_from) OVER (PARTITION BY country_code, indicator_id, year ORDER BY fetched_at, page_hash)
      AS earlier_public_from
  FROM scores
),
versions AS (
  SELECT
    country_code,
    country_iso3,
    indicator_id,
    indicator_name,
    year,
    value,
    CASE WHEN earlier_value IS NOT NULL AND public_from <= earlier_public_from
         THEN greatest(public_from, CAST(fetched_at AS DATE))
         ELSE public_from END AS public_from
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
