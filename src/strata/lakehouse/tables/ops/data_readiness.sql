-- The data readiness measures each run writes, per source and country (spec, "Data readiness and
-- the dashboard"). Each measure is a count with its denominator, or a date; there is no composite
-- score. The queries that compute them are in src/strata/lakehouse/readiness/, one per source.
--
-- run_id        the nightly job run that measured it; "fixture" in the gate's fixture database
-- source        the source registry's key
-- country_code  the country the rows belong to
-- measure       coverage_rows, coverage_years, linked_step_reference, linked_notice,
--               linked_project, contact_details_removed, fresh_fetched or fresh_newest_record
-- numerator     the count measured
-- denominator   what it is counted out of
-- as_of         for a freshness measure: the day of the last fetch, or of the newest record
-- detail        what the count means, as a full sentence, or the source's cadence for a freshness
--               measure. It is for people who query this table; screens take their words from
--               web/src/copy.ts.
-- measured_at   when the run measured it, in UTC
-- public_from   the day it was measured (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.data_readiness (
  run_id STRING NOT NULL,
  source STRING NOT NULL,
  country_code STRING NOT NULL,
  measure STRING NOT NULL,
  numerator BIGINT,
  denominator BIGINT,
  as_of DATE,
  detail STRING,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
