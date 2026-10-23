-- Data readiness measures (GLOSSARY.md), each a count with its denominator, written by every run
-- that measures a source. There is no composite score. The Data readiness page (ticket 16) reads
-- the latest run's rows for each source and subject.
--
-- run_id       the run that measured it
-- source       the source registry's key, such as documents
-- subject      what was measured, such as a project ID
-- measure      what was counted, such as pages_read_route_b
-- kind         coverage, linked, read_well or fresh
-- count        how many
-- denominator  out of how many
-- measured_at  when, in UTC
-- public_from  the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.data_readiness (
  run_id STRING NOT NULL,
  source STRING NOT NULL,
  subject STRING NOT NULL,
  measure STRING NOT NULL,
  kind STRING NOT NULL,
  count BIGINT NOT NULL,
  denominator BIGINT NOT NULL,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
