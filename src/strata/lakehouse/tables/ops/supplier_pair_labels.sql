-- A person's label on a candidate pair of name matching for suppliers, from the labeling tool (ticket
-- 19): merge when the two sides are one supplier, no_merge when they are not. Labels measure how
-- often auto-merge is right (strata.ops.supplier_match_quality); they never merge or split a pair,
-- which only a review decision does. The server writes one row per label, as the app's own service
-- principal, with the labeler from the viewer the Databricks App forwarded. The latest label on a
-- pair counts. docs/PLAN.md section 5 aims at 1,000 labeled pairs.
--
-- pair_id      the pair, as strata.ops.supplier_pairs names it
-- left_key, right_key  its two sides
-- label        merge or no_merge
-- labeler      the user id the Databricks App forwarded
-- labeled_at   when, in UTC
-- public_from  the day it was labeled, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.supplier_pair_labels (
  pair_id STRING NOT NULL,
  left_key STRING NOT NULL,
  right_key STRING NOT NULL,
  label STRING NOT NULL,
  labeler STRING NOT NULL,
  labeled_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
