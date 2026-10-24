-- What people did with each item of the lesson review queue (ticket 29; docs/PLAN.md section 11, "Lesson
-- governance"): one row for each recommendation, decision or cross-check, with the person and their
-- reason. Two different people act on every new lesson and re-check, nobody acts on a lesson from their
-- own project, and an act never changes or leaves: a change of mind is a re-check. The app writes these
-- rows as its own service principal, with the viewer the Databricks App forwarded, never a person the
-- request names (src/strata/knowledge/lessons/review.py).
--
-- act_id       the act's id
-- item_id      the item it acted on (strata.ops.lesson_review_items)
-- act          recommend, decide or cross_check
-- stage        the stage the person saw: recommendation, decision or cross_check
-- outcome      for a new lesson: add, repeat (add its quote to a current lesson) or reject; for a re-check:
--              keep, change, retire_wrong or retire_outdated; for a cross-check: agree or disagree
-- repeat_of    for repeat: the current lesson it repeats (strata.ops.lesson_versions)
-- change       for a change, or an add with new words: the statement and tags it gives, as JSON
-- reason       the person's reason, as they wrote it; optional only when a cross-checker agrees
-- actor        who acted: the email the Databricks App forwarded
-- actor_name   their name in the roles file (config/roles.toml)
-- actor_role   their role there, such as lead procurement specialist
-- actor_region the region they acted for
-- acted_at     when, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_review_acts (
  act_id STRING NOT NULL,
  item_id STRING NOT NULL,
  act STRING NOT NULL,
  stage STRING NOT NULL,
  outcome STRING NOT NULL,
  repeat_of STRING,
  change STRING,
  reason STRING,
  actor STRING NOT NULL,
  actor_name STRING NOT NULL,
  actor_role STRING NOT NULL,
  actor_region STRING NOT NULL,
  acted_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
