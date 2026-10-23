-- A governance score (CPIA or WGI) for a country and year, one row per version the Indicators API
-- published. The API revises past values in place, so a revision is a new row and the earlier one
-- stays (ADR 0002). Join on a date with src/strata/lakehouse/sql/governance_score_as_of.sql, which
-- takes the version public on that date, so no model sees a revised value early. A score fetched
-- for the first time counts as public from the day the API last updated it, every past year's
-- score with it, so there is no score for dates before that day.
--
-- country_code    the API's two-letter country id, such as KE
-- indicator_id    such as IQ.CPA.IRAI.XQ or GOV_WGI_GE.EST
-- year            the calendar year the score describes
-- value           the score, as the API gives it
-- public_from     the day the API published this version (its lastupdated date)
-- superseded_on   the day the API published the next version; empty while this one is current
CREATE TABLE IF NOT EXISTS strata.gold.governance_score (
  country_code STRING NOT NULL,
  country_iso3 STRING,
  indicator_id STRING NOT NULL,
  indicator_name STRING,
  year INT NOT NULL,
  value DOUBLE NOT NULL,
  superseded_on DATE,
  public_from DATE NOT NULL
)
