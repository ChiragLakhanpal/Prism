-- Each reading of a completion report for the hindsight test (ticket 34; src/strata/estimates/hindsight_coding.py,
-- which ops/hindsight/code.py runs). Two coders each read a project's ICR, on their own, and say which risk factors
-- on the closed list (config/lessons.toml) it blamed; where they differ, one person reads the ICR Review, which
-- settles it. A reading writes one row per risk factor on the list, blamed or not, under one coding_id, so the
-- coders' agreement can be counted factor by factor. A coder who reads again writes a new coding, and the newest
-- coding of each coder and reading counts. A row never changes and never leaves.
--
-- coding_id         one reading: every row it wrote shares it
-- project_id        the project whose report was read
-- reading           icr, a coder's reading of the ICR; or icr_review, the reading of the ICR Review that settles
--                   where the two coders differ
-- document_id       the report read, and its version: the newest ICR, or the newest ICR Review, that no re-issue
-- document_version  had replaced (a re-issue replaces the earlier version)
-- coder             the coder's email, and their name
-- coder_name
-- risk_key          a risk factor's key on the closed list
-- blamed            whether the report blamed it
-- coded_at          when the reading was stored, in UTC
-- public_from       the day it was stored (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.hindsight_codings (
  coding_id STRING NOT NULL,
  project_id STRING NOT NULL,
  reading STRING NOT NULL,
  document_id STRING NOT NULL,
  document_version INT NOT NULL,
  coder STRING NOT NULL,
  coder_name STRING NOT NULL,
  risk_key STRING NOT NULL,
  blamed BOOLEAN NOT NULL,
  coded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
