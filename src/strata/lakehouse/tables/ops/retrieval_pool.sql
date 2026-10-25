-- Each notice query's pool of passages for the judges (ticket 32): the best passages of several search
-- setups, public before the query's date, merged, so the judges grade every passage any setup would rank in
-- its top pool_depth (config/thresholds.toml). Judges never see which setup found a passage or where it
-- ranked, so neither is shown, and each judge sees the pool in an order of their own
-- (strata.knowledge.retrieval.judging).
--
-- query_id     the query (strata.ops.retrieval_queries)
-- passage_id   a pooled passage
-- pooled_at    when the pool was made, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_pool (
  query_id STRING NOT NULL,
  passage_id STRING NOT NULL,
  pooled_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
