-- How often each pair of hindsight coders agreed, as it stood when the codings were reconciled (ticket 34;
-- src/strata/estimates/hindsight_coding.py). Each project both coders read gives one pair of answers per risk
-- factor on the closed list (blamed or not), and Cohen's kappa is counted over all of them with the judging tool's
-- own function (strata.knowledge.retrieval.judging.kappa, ticket 32).
--
-- coder_a, coder_b  the two coders' emails, in alphabetical order
-- projects          the projects both read
-- pairs             their pairs of answers: one per risk factor per project
-- agree             the pairs where they gave the same answer
-- kappa             Cohen's kappa over those pairs, at two decimals; empty below config/thresholds.toml's
--                   retrieval.min_pairs, so no statistic rests on fewer than 20 cases
-- computed_at       when it was counted, in UTC
-- public_from       the day it was counted (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.hindsight_agreement (
  coder_a STRING NOT NULL,
  coder_b STRING NOT NULL,
  projects INT NOT NULL,
  pairs INT NOT NULL,
  agree INT NOT NULL,
  kappa DOUBLE,
  computed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
