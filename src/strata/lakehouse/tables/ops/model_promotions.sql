-- Each decision on promoting a challenger to champion (ticket 44; docs/PLAN.md section 11, the estimates loop's gate:
-- it wins the backtest and a quarter in shadow, its coverage holds for each edition of the procurement rules, and the
-- model owner and the lead signed off). A refusal keeps every reason code that applied, for ticket 45's copy keys;
-- a promotion moved the champion alias (src/strata/estimates/promotion.py). Rows only join.
--
-- model             the registered model's name (config/models.toml)
-- version           the challenger's version
-- champion_version  the champion's version when it was decided
-- promoted          whether it became the champion
-- refusals          JSON: the reason codes, in order: no_backtest_win, no_shadow_win, edition_coverage,
--                   no_model_owner_sign_off, no_lead_sign_off; empty for a promotion
-- evidence          JSON: the counts and values each check read
-- decided_at        when, in UTC
-- public_from       the day it was decided (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.model_promotions (
  model STRING NOT NULL,
  version INT NOT NULL,
  champion_version INT,
  promoted BOOLEAN NOT NULL,
  refusals STRING NOT NULL,
  evidence STRING NOT NULL,
  decided_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
