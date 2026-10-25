-- The retrieval loop's leading indicator (ticket 32; docs/PLAN.md section 11): passage reports per 100
-- sources opened, by week and by kind of report. The weekly retrieval run appends the weeks it measured, so
-- the latest row of a week and kind gives it (strata.knowledge.retrieval.reports).
--
-- A source counts as opened in the week someone first opened it in the evidence drawer, because
-- strata.ops.evidence_opened keeps one row per viewer and source. Reports withdrawn or sent in a preview
-- never count.
--
-- week_start   the Monday the week starts on
-- kind         wrong_passage or not_useful
-- reports      reports of that kind sent that week and not withdrawn
-- opened       sources first opened that week
-- per_100      reports for every 100 sources opened, at one decimal, a tool column; empty when fewer than
--              min_opened sources were opened (config/thresholds.toml), so no rate rests on a few opens
-- computed_at  when the run measured it, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_feedback_weekly (
  week_start DATE NOT NULL,
  kind STRING NOT NULL,
  reports INT NOT NULL,
  opened INT NOT NULL,
  per_100 DOUBLE,
  computed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
