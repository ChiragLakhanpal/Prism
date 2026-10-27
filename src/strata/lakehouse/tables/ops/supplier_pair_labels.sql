-- A person's label on a candidate pair of name matching for suppliers, from the labeling tool (ticket
-- 19): merge when the two sides are one supplier, no_merge when they are not. Labels measure how
-- often auto-merge is right (strata.ops.supplier_match_quality); they never merge or split a pair,
-- which only a review decision does. The server writes one row per label, as the app's own service
-- principal, with the labeler from the viewer the Databricks App forwarded. The latest label on a
-- pair counts, and only while the pair still has the two names the label was given: a pair is keyed
-- by row positions, so a revised notice that lists its bidders in a new order gives an old key to
-- another firm (ticket 63). docs/PLAN.md section 5 aims at 1,000 labeled pairs.
--
-- pair_id      the pair, as strata.ops.supplier_pairs names it
-- left_key, right_key  its two sides
-- left_name, right_name  the pair's two names when it was labeled. Ticket 63 added them: a workspace
--              whose table is older runs
--              ALTER TABLE strata.ops.supplier_pair_labels ADD COLUMNS (left_name STRING, right_name STRING)
--              before the deploy that brings ticket 63, and an older label, with no names, counts no more
-- label        merge or no_merge
-- labeler      the user id the Databricks App forwarded
-- labeled_at   when, in UTC
-- public_from  the day it was labeled, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.supplier_pair_labels (
  pair_id STRING NOT NULL,
  left_key STRING NOT NULL,
  right_key STRING NOT NULL,
  left_name STRING,
  right_name STRING,
  label STRING NOT NULL,
  labeler STRING NOT NULL,
  labeled_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
