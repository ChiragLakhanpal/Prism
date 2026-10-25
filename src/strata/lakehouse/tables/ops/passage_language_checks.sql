-- The passages each document run checked against a language detector (ticket 42; src/strata/knowledge/language.py):
-- one row per sampled passage. Each passage takes its language from its document's record in the Documents API;
-- the detector reads only the passage's words, so the check does not rest on how the language was set. The
-- sample shares config/thresholds.toml's lang.sample_size equally between the languages the passages are written
-- in, and strata.ops.data_readiness's passage_language_sample_agrees counts the rows that agree.
--
-- run_id       the document run
-- passage_id   the passage checked, as in strata.silver.passages
-- language     the language the passage carries, as an ISO 639-1 code
-- detected     the language the detector read in its words, from the languages config/languages.toml lists
-- confidence   how sure the detector was, from 0 to 1
-- agrees       whether the two are the same
-- detector     the detector and its version
-- measured_at  when, in UTC
-- public_from  the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.passage_language_checks (
  run_id STRING NOT NULL,
  passage_id STRING NOT NULL,
  language STRING NOT NULL,
  detected STRING NOT NULL,
  confidence DOUBLE NOT NULL,
  agrees BOOLEAN NOT NULL,
  detector STRING NOT NULL,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
