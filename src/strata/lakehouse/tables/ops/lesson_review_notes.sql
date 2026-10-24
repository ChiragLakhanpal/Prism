-- What the lesson review writer wrote about each item of the lesson review queue (ticket 29; the 29 design
-- brief, section 4.6): its summary of the item's evidence and the current lessons the item may repeat, as
-- the verifier left them. The review-proposed-lessons workflow (src/strata/knowledge/lessons/writer.py)
-- writes a row when an item enters the queue, and again when the library has changed since, so the review
-- page renders from a stored row with no model call while a reviewer waits. The page shows the newest row.
-- A row never changes and never leaves.
--
-- item_id        the queue item (strata.ops.lesson_review_items)
-- written_at     when the workflow wrote it, in UTC
-- status         ready, nothing_to_add (the writer had nothing to add to the quotes), nothing_survived
--                (the verifier removed every sentence) or failed (the writer gave no answer)
-- content        the kept sentences with their evidence ids, the evidence they cite, the verifier's counts,
--                the removed sentences with their reasons, and the likely repeats, each a current lesson's
--                id and version with its kept sentences, as JSON
-- library_versions  how many lesson versions the library held when it was written, so the workflow knows to
--                write again once a decision changes the library
-- agent          the writer agent's name and version
-- agent_version
-- error          why the writer gave no answer, for a failed row
-- public_from    the day it was written (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_review_notes (
  item_id STRING NOT NULL,
  written_at TIMESTAMP NOT NULL,
  status STRING NOT NULL,
  content STRING,
  library_versions INT NOT NULL,
  agent STRING,
  agent_version STRING,
  error STRING,
  public_from DATE NOT NULL
)
