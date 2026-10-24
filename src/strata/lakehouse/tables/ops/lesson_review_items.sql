-- The lesson review queue (ticket 29; docs/PLAN.md section 11): one row for each item people decide on.
-- A new lesson enters when the nightly job's propose_lessons task finds a proposal whose quote passed the
-- check; a re-check when a lesson reviewer asks for one, when a cross-check disagrees, or when a new edition
-- of the procurement rules takes effect for a lesson's projects; a cross-check when the quarterly job
-- assigns a decision to another region. What people then do is in strata.ops.lesson_review_acts, so an
-- item's row never changes and no row is ever deleted.
--
-- item_id          the item's id in its address (/lessons/review/{item_id}), such as new-3f2a9c1d0b
-- kind             new, recheck or cross_check
-- proposal_id      a new lesson's proposal (strata.silver.lesson_proposals)
-- lesson_id        a re-check's or a cross-check's lesson
-- version          the lesson version it re-checks or cross-checks
-- decided_item_id  a cross-check's item: the one whose decision it checks
-- project_id       the project the lesson comes from, for recusal
-- region           the region whose reviewers act on it, as strata.gold.project.region writes it; for a
--                  cross-check, the region the quarterly job assigned
-- decided_region   a cross-check's region that decided
-- origin           proposed (the nightly job), asked (a reviewer), cross_check (a disagreement), edition
--                  (a new edition took effect) or quarterly (the cross-check job)
-- origin_by        who asked for a re-check or disagreed: the email the app forwarded
-- origin_by_name   their name from the roles file
-- origin_reason    their reason, as they wrote it
-- origin_item_id   the cross-check whose disagreement started a re-check
-- entered_on       the day it entered the queue, day 1 of its business-day clock
-- due_on           a cross-check's due day, set by the quarterly job; empty for the others, whose due day
--                  the clock counts from entered_on (config/thresholds.toml, lesson_review)
-- created_at       when the row was written, in UTC
-- public_from      entered_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_review_items (
  item_id STRING NOT NULL,
  kind STRING NOT NULL,
  proposal_id STRING,
  lesson_id STRING,
  version INT,
  decided_item_id STRING,
  project_id STRING NOT NULL,
  region STRING NOT NULL,
  decided_region STRING,
  origin STRING NOT NULL,
  origin_by STRING,
  origin_by_name STRING,
  origin_reason STRING,
  origin_item_id STRING,
  entered_on DATE NOT NULL,
  due_on DATE,
  created_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
