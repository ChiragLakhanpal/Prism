-- One row for each draft Strata wrote for a person to check (ticket 35), saved only once its writer and
-- the verifier finished: review notes on a plan, and the kinds later tickets add (config/drafts.toml).
-- The draft runtime (src/strata/drafts/store.py) writes it as the app's own service principal, and every
-- read goes through the one access rule in src/strata/server/access.py, which shows a draft only to its
-- author's team. A draft's state is its latest row in strata.ops.draft_states. Nothing deletes a draft:
-- Discard writes a state row, and Restore writes another.
--
-- Drafts render as they are today, so no read filters them by public_from.
--
-- draft_id         the draft's id, shown on its page
-- kind             its kind in config/drafts.toml, such as review_notes
-- team_key         its author's team when it was saved: team:<key> from config/roles.toml, or
--                  viewer:<user id> for a viewer on no team
-- author_id        the user id the Databricks App forwarded for its author
-- author_name      its author's name as the App forwarded it, which teammates read on the page
-- idempotency_key  the key the browser sent, so a second request with the same key saves nothing new
-- project_id       the project it is about
-- subject          what it was written from, such as the plan version's document id
-- content          the draft as JSON: its notes, the sentences the verifier kept, the evidence they cite,
--                  the verifier's counts and the sentences it removed
-- created_at       when it was saved, in UTC
-- public_from      the day it was saved, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.drafts (
  draft_id STRING NOT NULL,
  kind STRING NOT NULL,
  team_key STRING NOT NULL,
  author_id STRING NOT NULL,
  author_name STRING,
  idempotency_key STRING,
  project_id STRING,
  subject STRING,
  content STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
