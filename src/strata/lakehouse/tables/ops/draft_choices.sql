-- Which report a draft's author kept on each disagreement card under the draft (ticket 36; brief 23's keep form):
-- the report the draft already rests on (lean), or the other one with a reason (other). One row per choice, so the
-- history is never rewritten; going back to Strata's choice is a new row with lean. strata.ops.draft_choices_latest
-- gives each card's latest choice, which the disagreements hold and the evidence pack read. The draft routes
-- (src/strata/server/drafts.py) write each row from the author's session, as the app's own service principal.
--
-- draft_id         the draft, in strata.ops.drafts
-- save_no          the choice's number in the draft's history, from 1
-- disagreement_id  the disagreement's evidence id, as check 6 attached it to the draft
-- kept             lean or other
-- reason           why the other report was kept; empty for lean
-- set_by_id        the user id of the person who chose, always the draft's author
-- set_by_name      their name as the Databricks App forwarded it
-- set_at           when they chose, in UTC
-- public_from      the day they chose, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.draft_choices (
  draft_id STRING NOT NULL,
  save_no INT NOT NULL,
  disagreement_id STRING NOT NULL,
  kept STRING NOT NULL,
  reason STRING,
  set_by_id STRING NOT NULL,
  set_by_name STRING,
  set_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
