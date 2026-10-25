-- The queries written from award notices, for the judging tool (ticket 32; the spec's "Evaluation": 150
-- queries written from award notices and judged by two people). The search owner writes them in
-- evals/retrieval_queries.toml, and loading them appends one row per query with its two query judges from
-- the roles file. The latest row of a query gives it (strata.knowledge.retrieval.judging).
--
-- query_id     the query's id in the file
-- n            its number, which Judging shows ("Query 3")
-- query_text   the query's words
-- notice_id    the award notice it was written from (strata.gold.notice)
-- notice_ref   the notice's STEP reference or bid reference, as Judging shows it
-- notice_date  the day the notice was published: the query's date, before which every pooled passage was
--              public
-- project_id   the notice's project
-- judges       the two query judges, by email, as a JSON list
-- loaded_at    when it was loaded, in UTC
-- public_from  the day it was loaded, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_queries (
  query_id STRING NOT NULL,
  n INT NOT NULL,
  query_text STRING NOT NULL,
  notice_id STRING NOT NULL,
  notice_ref STRING,
  notice_date DATE NOT NULL,
  project_id STRING,
  judges STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
