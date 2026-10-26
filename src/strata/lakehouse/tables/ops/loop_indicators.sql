-- Each loop's indicators on the dashboard's AI quality and adoption page (ticket 45; the 45 design brief, section
-- 7.4, tile 19): six rows, a leading and a lagging indicator for each of the knowledge, retrieval and estimates loops,
-- written each night in words from the KPI registry's queries (config/kpis.toml; strata.dashboard.findings), with
-- the target and where the latest value stands against it in words, never a color. Each write appends its rows; the
-- dashboard reads the newest write.
--
-- run_id       the nightly run that wrote it
-- position     1 to 6, in loop order
-- kpi          the KPI's id in config/kpis.toml
-- loop         the loop, in words
-- indicator    the indicator's name (copy.kpi.<id>.name)
-- kind         Leading or Lagging
-- latest       the latest value with its counts, or the counts alone when too few
-- target       its target in words, or "None set"
-- against      where the latest value stands against the target, in words
-- measured_on  the day the measure was taken; empty when it has never been taken
-- written_at   when it was written, in UTC
-- public_from  the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.loop_indicators (
  run_id STRING NOT NULL,
  position INT NOT NULL,
  kpi STRING NOT NULL,
  loop STRING NOT NULL,
  indicator STRING NOT NULL,
  kind STRING NOT NULL,
  latest STRING NOT NULL,
  target STRING NOT NULL,
  against STRING NOT NULL,
  measured_on DATE,
  written_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
