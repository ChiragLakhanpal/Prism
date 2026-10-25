-- The sources each answer cited (ticket 32): one row for each kept sentence and each evidence id it cites,
-- written when an answer stream ends, beside its run in strata.ops.agent_runs. A passage report reads it to
-- check the passage came back in that answer and to take the question and the sentence from the run, never
-- from the browser. The retrieval loop reads it to count the answers that cite a different paragraph after
-- a reviewer ranked a reported passage lower (strata.knowledge.retrieval.reports). viewer_id is masked, so only
-- the app and the catalog's owner read who asked (src/strata/lakehouse/masks.py; ticket 64).
--
-- run_id          the answer (strata.ops.agent_runs)
-- viewer_id       who asked: the user id the Databricks App forwarded (masked)
-- question        what they asked
-- query_kind      the kind of question (config/retrieval.toml) of the search that found the source, for a passage
--                 search_passages found; otherwise the kind of the person's question
-- as_of           the date the answer read its sources as of
-- view            the view it was asked in: staff, piu or public
-- sentence_index  the sentence's index in the answer
-- sentence        the sentence, as the answer wrote it
-- evidence_id     a source the sentence cites
-- tool            the tool that returned it, such as search_passages
-- project_id      the source's project, when it has one
-- asked_at        when the answer finished, in UTC
-- public_from     the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.answer_citations (
  run_id STRING NOT NULL,
  viewer_id STRING,
  question STRING NOT NULL,
  query_kind STRING NOT NULL,
  as_of DATE NOT NULL,
  view STRING NOT NULL,
  sentence_index INT NOT NULL,
  sentence STRING NOT NULL,
  evidence_id STRING NOT NULL,
  tool STRING,
  project_id STRING,
  asked_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
