-- What a draft's author chose for a row that cites a lesson a lead has since changed or retired (ticket 39; the
-- 39 brief, sections 4.4 to 4.6). Nothing in a draft changes without its author, so a version notice stays on the
-- row until one of these is written. Each choice is a new row and nothing leaves (CLAUDE.md rule 5): removing a
-- row writes "remove" and restoring it writes "restore"; "Go back to version {a}" writes "revert". The draft store
-- (strata.drafts.store) reads them in order and shows the draft as they leave it, so the stored draft itself is
-- never rewritten.
--
-- draft_id         the draft, in strata.ops.drafts
-- choice_no        the choice's number in the draft's history, from 1
-- row_key          the draft's row (a suggested PPSD row's risk key, or a note's key)
-- lesson_id        the lesson the row cites
-- action           update (the row was rewritten from the current version and checked again), keep (the author
--                  kept the version the row cites, with a reason), remove, restore, or revert (an update undone)
-- cited_version    the version the row cited when the author chose
-- current_version  the lesson's newest version when the author chose
-- reason           the author's reason, for keep; empty otherwise. Masked from every reader but the app and the
--                  owner (strata.lakehouse.masks)
-- rewrite          for update, the row's new notes as JSON: the sentences the verifier kept, the evidence they
--                  cite, the sentences it removed and its counts; empty otherwise. Masked from every reader but the
--                  app and the owner (strata.lakehouse.masks)
-- draft_state      the draft's state when the author chose: draft or checked
-- actor_id         the user id of the author, as the Databricks App forwarded it
-- actor_name       their name
-- chosen_at        when, in UTC
-- public_from      the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.draft_lesson_choices (
  draft_id STRING NOT NULL,
  choice_no INT NOT NULL,
  row_key STRING NOT NULL,
  lesson_id STRING NOT NULL,
  action STRING NOT NULL,
  cited_version INT NOT NULL,
  current_version INT NOT NULL,
  reason STRING,
  rewrite STRING,
  draft_state STRING NOT NULL,
  actor_id STRING NOT NULL,
  actor_name STRING,
  chosen_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
