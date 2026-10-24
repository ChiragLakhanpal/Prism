-- CPIA and WGI values from the Indicators API, typed: one row per country, indicator and year from
-- each fetched page. A page the API republished with a changed value is a new version, and its rows
-- sit beside the earlier ones; gold.governance_score keeps each version.
--
-- indicator_id     such as IQ.CPA.IRAI.XQ or GOV_WGI_GE.EST
-- country_code     the API's two-letter country id, such as KE; regions and income groups have one too
-- country_iso3     the API's countryiso3code
-- year             the calendar year the value describes
-- value            the score; empty for a year with no score
-- last_updated     the page's lastupdated: the day the API last published the indicator
-- public_from      last_updated, or the fetch day when it is missing or later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.indicators (
  indicator_id STRING NOT NULL,
  indicator_name STRING,
  country_code STRING,
  country_iso3 STRING,
  country_name STRING,
  year INT,
  value DOUBLE,
  last_updated DATE,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
