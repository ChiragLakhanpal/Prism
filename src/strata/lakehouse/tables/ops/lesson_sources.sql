-- Which proposals' evidence each lesson rests on, from the version that added it (ticket 29). A lead's
-- decision to add a proposed lesson links its proposal at version 1; a merge links the merged proposal at
-- the target's new version. The quotes, pages and restatements are in strata.silver.lesson_evidence, so a
-- restatement IEG publishes later still reaches the lesson. A row never changes and never leaves.
--
-- lesson_id    the lesson (strata.ops.lesson_versions)
-- version      the version that added this evidence
-- proposal_id  the proposal whose evidence it adds (strata.silver.lesson_proposals)
-- item_id      the queue item whose decision added it
-- public_from  the day it was added (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_sources (
  lesson_id STRING NOT NULL,
  version INT NOT NULL,
  proposal_id STRING NOT NULL,
  item_id STRING NOT NULL,
  public_from DATE NOT NULL
)
