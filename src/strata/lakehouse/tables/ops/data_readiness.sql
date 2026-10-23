-- The data readiness measures each run writes (GLOSSARY.md; spec, "Data readiness and the
-- dashboard"). Each measure is a count with its denominator, or for a freshness measure a date;
-- there is no composite score. The Data readiness page (ticket 16) reads the latest run's rows for
-- each source and subject. Two writers fill it: the nightly job, from one query per source in
-- src/strata/lakehouse/readiness/, and the plan reader (src/strata/lakehouse/plans.py).
--
-- run_id       the run that measured it; "fixture" for the nightly job's run in the gate's fixture
--              database
-- source       the source registry's key, such as awards or documents
-- subject      what was measured: a country's two-letter code (KE) for the records the nightly job
--              fetches, or a project ID (P156634) for its Procurement Plans
-- measure      what was counted, such as linked_step_reference or pages_read_route_b
-- kind         coverage, linked, read_well or fresh, or stripped for the contact details removed
--              (the dashboard's Governance page shows personal data stripped)
-- count        how many; empty for a freshness measure
-- denominator  out of how many; empty for a freshness measure
-- as_of        for a freshness measure: the day of the last fetch, or of the newest record
-- detail       what the count means, as a full sentence, or the source's cadence for a freshness
--              measure. It is for people who query this table; screens take their words from
--              web/src/copy.ts.
-- measured_at  when, in UTC
-- public_from  the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.data_readiness (
  run_id STRING NOT NULL,
  source STRING NOT NULL,
  subject STRING NOT NULL,
  measure STRING NOT NULL,
  kind STRING NOT NULL,
  count BIGINT,
  denominator BIGINT,
  as_of DATE,
  detail STRING,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
