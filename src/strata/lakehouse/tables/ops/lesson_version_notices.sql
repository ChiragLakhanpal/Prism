-- The version notices the nightly job's refresh_drafts task sets (ticket 43; the 39 brief, sections 4.1 and 9):
-- one row for each open draft row that cites a lesson at a version a lead has since changed or retired, and
-- for each newer version the job found. The task never changes a draft (GLOSSARY.md, "Lesson version"): it
-- only adds these rows, which the draft page and the Lessons tab read. A lesson that only gained a quote
-- ("strengthened") marks no draft, so it has no row here. A row never changes and never leaves.
--
-- draft_id         the draft, in strata.ops.drafts
-- row_key          the draft's row (its note's key) that cites the lesson
-- lesson_id        the lesson cited
-- cited_version    the version the row cites
-- current_version  the lesson's newest version when the job looked
-- tier             the strongest change since the cited version: narrowed (its wording or tags changed),
--                  retired_outdated or retired_wrong (strata.knowledge.lessons.notices.tier)
-- holds_export     whether the change keeps the draft from export until its author chooses: only retired_wrong
-- decided_on       the day the current version was decided
-- run_id           the nightly run that set it
-- noticed_at       when, in UTC
-- public_from      the day it was set, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_version_notices (
  draft_id STRING NOT NULL,
  row_key STRING NOT NULL,
  lesson_id STRING NOT NULL,
  cited_version INT NOT NULL,
  current_version INT NOT NULL,
  tier STRING NOT NULL,
  holds_export BOOLEAN NOT NULL,
  decided_on DATE NOT NULL,
  run_id STRING NOT NULL,
  noticed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
