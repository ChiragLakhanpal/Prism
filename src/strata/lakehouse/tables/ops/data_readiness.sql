-- The data readiness measures each run writes (GLOSSARY.md; spec, "Data readiness and the
-- dashboard"). Each measure is a count with its denominator, or for a freshness measure a date;
-- there is no composite score. The Data readiness page (ticket 16) reads, for each source, subject
-- and measure, the row from the latest run that wrote that measure: the newest measured_at, since
-- as_of is set only on the freshness measures. It never sums or averages over runs. Three writers fill it: the
-- nightly job, from one query per source in src/strata/lakehouse/readiness/, the plan reader
-- (src/strata/lakehouse/plans.py) and the passage reader (src/strata/lakehouse/passages.py). The plan
-- reader and the passage reader both write the documents source for a project, under different
-- runs, so each gives its measures names the other never uses.
--
-- run_id       the run that measured it; "fixture" for the nightly job's run in the gate's fixture
--              database
-- source       the source registry's key, such as awards or documents
-- subject      what was measured: a country's two-letter code (KE) for the records the nightly job
--              fetches, or a project ID (P156634) for its documents: its Procurement Plans, and
--              the reports the passage reader reads
-- measure      what was counted, such as linked_step_reference, pages_read_route_b (the plan
--              reader) or document_pages_route_b (the passage reader)
-- kind         coverage, linked, read_well or fresh, or stripped for the contact details removed
--              (the dashboard's Governance page shows personal data stripped), screened for what
--              Prompt Shields found in the passages, or fix for what a fix on the Data readiness
--              page would unlock, such as the projects it would add evidence to
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
