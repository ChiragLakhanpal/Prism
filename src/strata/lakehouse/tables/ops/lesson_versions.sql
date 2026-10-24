-- Each version of each lesson in the library (ticket 29; the spec's knowledge model: a lesson is current at
-- a version, and each version records was, now and the reason). A lead procurement specialist's decision
-- writes a new row: version 1 when a proposed lesson is added, then one more for each merge, change or
-- retirement. A row never changes and never leaves, so a draft that cites a version can always open it.
-- strata.knowledge.lessons.review and get_lessons read the newest version of each lesson.
--
-- lesson_id            the lesson's id, the same at every version: lesson-3f2a9c1d0b
-- version              1, 2, 3 ...
-- statement            the lesson in one sentence
-- risk_factors         the risk factors' keys, as a JSON list (config/lessons.toml)
-- stage, kind          their keys (config/lessons.toml)
-- edition_key          the edition of the procurement rules its project followed (config/editions.toml)
-- project_id           the project its first evidence came from
-- state                current, retired_wrong or retired_outdated
-- change_kind          what this version changed: added, merged, wording, tags or retired
-- was, now             what it changed from and to, as JSON: the statement and tags, or for a merge the
--                      quotes and reports it rests on; empty for a lesson added as proposed
-- reason               the lead's reason, as written
-- item_id              the queue item decided (strata.ops.lesson_review_items)
-- decided_on           the day it was decided, in UTC
-- decided_by           the lead who decided: the email the app forwarded, their name and their role
-- decided_by_name
-- recommended_by       who recommended it: their email and name, and their reason
-- recommended_by_name
-- recommended_reason
-- published_on         the day the report the lesson came from became public; for version 1 only
-- days_from_publication  days from published_on to decided_on, the knowledge loop's leading indicator
--                      (docs/PLAN.md section 11); for version 1 only
-- public_from          decided_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_versions (
  lesson_id STRING NOT NULL,
  version INT NOT NULL,
  statement STRING NOT NULL,
  risk_factors STRING NOT NULL,
  stage STRING NOT NULL,
  kind STRING NOT NULL,
  edition_key STRING,
  project_id STRING NOT NULL,
  state STRING NOT NULL,
  change_kind STRING NOT NULL,
  was STRING,
  now STRING,
  reason STRING NOT NULL,
  item_id STRING NOT NULL,
  decided_on DATE NOT NULL,
  decided_by STRING NOT NULL,
  decided_by_name STRING NOT NULL,
  recommended_by STRING NOT NULL,
  recommended_by_name STRING NOT NULL,
  recommended_reason STRING NOT NULL,
  published_on DATE,
  days_from_publication INT,
  public_from DATE NOT NULL
)
