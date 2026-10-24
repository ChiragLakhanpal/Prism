-- A person's decision on a candidate pair of name matching for suppliers: merge or no merge, with the
-- reviewer and the reason (ticket 19). The server writes one row per decision, as the app's own
-- service principal (src/strata/server/suppliers.py), and takes the reviewer from the viewer the
-- Databricks App forwarded with the request. The latest decision on a pair stands, and the next
-- nightly run applies it. No roles file names the reviewers yet (tickets 29 and 38 bring it), so any
-- signed-in viewer can decide.
--
-- The rows keep the user id, not the email, as strata.ops.evidence_opened does: every account user
-- can read strata.ops (bundle/catalog.yml).
--
-- pair_id      the pair, as strata.ops.supplier_pairs names it
-- left_key, right_key  its two sides
-- decision     merge or no_merge
-- reviewer     the user id the Databricks App forwarded
-- reason       the reviewer's reason, in their words
-- decided_at   when, in UTC
-- public_from  the day it was decided, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.supplier_review_decisions (
  pair_id STRING NOT NULL,
  left_key STRING NOT NULL,
  right_key STRING NOT NULL,
  decision STRING NOT NULL,
  reviewer STRING NOT NULL,
  reason STRING NOT NULL,
  decided_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
