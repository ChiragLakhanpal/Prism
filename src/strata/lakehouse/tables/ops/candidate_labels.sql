-- Passage reports from the evidence drawer (ticket 32; docs/PLAN.md section 11, "Feedback"): each row a
-- candidate label, never production data. A person marks a passage a search found for their question as
-- "Wrong passage" or "Not useful", with an optional reason, and the app writes one 'sent' row with the
-- viewer, the passage, the question and the reason. Withdrawing the report writes a 'withdrawn' row with
-- the same report_id; nothing changes or leaves. Ranking changes only when a passage reviewer accepts the
-- report's group, or at scale when the weekly run makes a silver label (strata.ops.label_decisions). The
-- app writes these rows as its own service principal, with the viewer the Databricks App forwarded
-- (src/strata/knowledge/retrieval/reports.py), and reads them back as itself: viewer_id and viewer_email are
-- masked, so every other reader reads NULL there (src/strata/lakehouse/masks.py; ticket 64).
--
-- report_id      the report's id; a withdrawal repeats it
-- event          sent or withdrawn
-- viewer_id      who sent it: the user id the Databricks App forwarded (masked)
-- viewer_email   their email, so the roles file can name their role and their projects (masked)
-- viewer_role    the role a review page names them by: staff, piu or public (never their name)
-- evidence_id    the passage, as an evidence id (strata.gold.passage:<passage_id>)
-- passage_id     the passage's id
-- project_id     the passage's project
-- run_id         the answer it was opened from (strata.ops.agent_runs)
-- sentence_index the answer's sentence that cited it
-- sentence       that sentence, as the answer wrote it
-- question       the question the answer answered
-- query_kind     the kind of question (config/retrieval.toml) of the search that found the passage, which a
--                decision ranks it lower for
-- kind           wrong_passage or not_useful
-- reason         the reason the person gave, as they wrote it, or empty
-- as_of          the as-of date the answer was read as of
-- own_project    whether the roles file lists the sender on the passage's project
-- reported_at    when, in UTC
-- public_from    the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.candidate_labels (
  report_id STRING NOT NULL,
  event STRING NOT NULL,
  viewer_id STRING NOT NULL,
  viewer_email STRING,
  viewer_role STRING NOT NULL,
  evidence_id STRING NOT NULL,
  passage_id STRING NOT NULL,
  project_id STRING,
  run_id STRING NOT NULL,
  sentence_index INT,
  sentence STRING,
  question STRING NOT NULL,
  query_kind STRING NOT NULL,
  kind STRING NOT NULL,
  reason STRING,
  as_of DATE,
  own_project BOOLEAN NOT NULL,
  reported_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
