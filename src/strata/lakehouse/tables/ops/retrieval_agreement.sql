-- How often each pair of query judges agreed (ticket 32; the spec's "Evaluation": two judges per notice query,
-- with their agreement statistic). The weekly retrieval run appends one row per pair of judges, over every
-- passage both graded on the queries both finished, so the dashboard and the replay harness read the agreement as
-- it was on a date (strata.knowledge.retrieval.judging). The latest row of a pair gives it.
--
-- judge_a      one judge, by email: the earlier of the two in alphabetical order
-- judge_b      the other judge
-- both_done    how many queries both finished
-- pairs        how many passages both graded on those queries
-- agree        on how many of them their grades matched
-- kappa        Cohen's kappa over those passages, at two decimals; empty below config/thresholds.toml's
--              retrieval.min_pairs, where Judging withholds it too
-- computed_at  when the weekly run worked it out, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_agreement (
  judge_a STRING NOT NULL,
  judge_b STRING NOT NULL,
  both_done INT NOT NULL,
  pairs INT NOT NULL,
  agree INT NOT NULL,
  kappa DOUBLE,
  computed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
