-- Each sign-off on a challenger model version (ticket 44; docs/PLAN.md section 11: the estimates loop's owner is the
-- model owner, co-signed by the lead). A challenger becomes the champion only with a sign-off from a member of the
-- roles file's model owner group and one from a different person in its lead group ([model_sign_off] in
-- config/roles.toml), beside its backtest win, its shadow-quarter win and its coverage for each edition
-- (src/strata/estimates/promotion.py). Rows only join.
--
-- model        the registered model's name (config/models.toml)
-- version      the challenger's version
-- role         model_owner or lead
-- signed_by    the email the person signed in with
-- signed_at    when, in UTC
-- public_from  the day they signed (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.model_signoffs (
  model STRING NOT NULL,
  version INT NOT NULL,
  role STRING NOT NULL,
  signed_by STRING NOT NULL,
  signed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
