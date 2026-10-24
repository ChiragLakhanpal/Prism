-- Each time an answer or a draft cited a lesson version (tickets 35 and 39 write it; ticket 29 defines it,
-- so the rule below has a table to hold to). get_lessons never reads it: lessons are ranked by fit and
-- evidence, never by how often they were used (spec story 98; docs/PLAN.md section 11, "Loops through the
-- world"), and tests/test_get_lessons.py changes these counts to prove the order does not move.
--
-- lesson_id    the lesson cited
-- version      the version cited
-- used_in      what cited it: an answer's run id or a draft's id
-- used_by      who saw it: the email the app forwarded
-- used_at      when, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_uses (
  lesson_id STRING NOT NULL,
  version INT NOT NULL,
  used_in STRING NOT NULL,
  used_by STRING,
  used_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
