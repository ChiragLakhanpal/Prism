-- Every state a draft has been in (ticket 35), one row per change, so its history is never rewritten.
-- A draft starts in draft when it is saved, and only its author moves it on: to checked (Checked by you),
-- to exported, or to discarded and back to the state it was discarded from. The latest step is its state
-- now. The draft runtime (src/strata/drafts/store.py) writes each row as the app's own service principal,
-- and only when the state the author saw is still the latest one.
--
-- draft_id     the draft, in strata.ops.drafts
-- step         its number in the draft's history, from 1
-- state        draft, checked, exported or discarded
-- from_state   the state before it, which Restore returns a discarded draft to
-- actor_id     the user id of the person who moved it, or of its author for the first step
-- actor_name   their name as the Databricks App forwarded it
-- changed_at   when it changed, in UTC
-- public_from  the day it changed, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.draft_states (
  draft_id STRING NOT NULL,
  step INT NOT NULL,
  state STRING NOT NULL,
  from_state STRING,
  actor_id STRING NOT NULL,
  actor_name STRING,
  changed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
