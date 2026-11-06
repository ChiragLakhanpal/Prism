-- One row each time a person keeps one side of a disagreement for an answer or a draft (ticket 23): keeping the
-- report Prism did not lean on, with their reason, or going back to Prism's choice. Rows are only ever added,
-- never changed or deleted, so the evidence pack (ticket 35) reads the latest row per viewer, disagreement and
-- answer or draft, and can list every reason given. The server writes it as the app's own service principal
-- (src/strata/server/choices.py), with the viewer the Databricks App forwarded. A preview of another view writes
-- nothing. The column names are a contract with ticket 35.
--
-- The rows keep no email: every account user can read strata.ops (bundle/catalog.yml), and the user id is enough
-- to tell people apart.
--
-- choice_id            a random id for the row
-- viewer               the user id the Databricks App forwarded
-- disagreement_id      the disagreement, as strata.gold.disagreement keys it, such as 437378890475ef48
-- kept_assertion_id    the side the person kept, as strata.gold.assertion keys it
-- leaned_assertion_id  the side Prism leans on; equal to kept_assertion_id when the person went back to it
-- reason               why they kept the other side, in their words, at most 500 characters; empty on going back
-- run_id               the answer the choice belongs to (strata.ops.agent_runs), or empty for a draft
-- draft_id             the draft the choice belongs to (strata.ops.drafts), or empty for an answer
-- made_at              when the choice was made, in UTC
-- public_from          the day it was made, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.disagreement_choices (
  choice_id STRING NOT NULL,
  viewer STRING NOT NULL,
  disagreement_id STRING NOT NULL,
  kept_assertion_id STRING NOT NULL,
  leaned_assertion_id STRING NOT NULL,
  reason STRING,
  run_id STRING,
  draft_id STRING,
  made_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
