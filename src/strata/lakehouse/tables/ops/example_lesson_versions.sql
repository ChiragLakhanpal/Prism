-- The example lesson change (ticket 41; the 41 design brief, section 4.5): a version of one lesson that a seeded draft
-- cites, with a changed wording, that only its one viewer sees, so the panel can see how a changed lesson reaches a
-- draft. It is kept apart from strata.ops.lesson_versions on purpose: the library, the Lessons digest and every other
-- viewer read only the lead's versions there, and an example never changes what other people see. Only that viewer's
-- notices, draft page and two-versions view add it. Written once by the seed command, as the app's own service
-- principal; a row is added only when none exists for the viewer, lesson and version (CLAUDE.md rule 5).
--
-- viewer_id    the user id the Databricks App forwards for the viewer
-- lesson_id    the lesson, such as lesson-e903b07ad1
-- version      the example version's number, one after the lesson's latest version when it was set up
-- version_row  the version as strata.knowledge.lessons.review's lesson_versions query returns a row, as JSON, with
--              example true and decided_by strata
-- seeded_at    when, in UTC
-- public_from  the day it was set up, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.example_lesson_versions (
  viewer_id STRING NOT NULL,
  lesson_id STRING NOT NULL,
  version INT NOT NULL,
  version_row STRING NOT NULL,
  seeded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
