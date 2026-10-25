-- The query judges' grades (ticket 32): one row each time a judge grades a pooled passage. A judge may change
-- a grade until both judges finish the query, and each change is a new row, so the latest row of a judge and
-- passage gives the grade. Once both finish, the query's grades lock and count toward the labeled set and
-- the judges' agreement (Cohen's kappa, strata.knowledge.retrieval.judging).
--
-- grade_id     the row's id
-- query_id     the query (strata.ops.retrieval_queries)
-- passage_id   the passage graded
-- judge_email  the judge: the email the Databricks App forwarded
-- judge_name   their name in the roles file
-- grade        answers (it answers the query), partly or not_relevant
-- graded_at    when, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_grades (
  grade_id STRING NOT NULL,
  query_id STRING NOT NULL,
  passage_id STRING NOT NULL,
  judge_email STRING NOT NULL,
  judge_name STRING,
  grade STRING NOT NULL,
  graded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
