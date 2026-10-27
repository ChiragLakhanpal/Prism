-- The review list for suppliers (ticket 19): each candidate pair of name matching that waits for a
-- person, from the latest run of strata.ops.supplier_pairs, with both names, countries and contracts.
-- A pair is here when the model was not sure enough of it (model_unsure), when merging it would join
-- two STEP supplier IDs by name (two_step_supplier_ids), when other merges would join two rows a person
-- said are not one supplier (person_kept_apart), or when no model could judge it (no_model).
-- A person decides merge or no merge, with a reason, through POST /api/suppliers/review
-- (src/strata/server/suppliers.py); the decision lands in strata.ops.supplier_review_decisions and the
-- next nightly run applies it. An individual consultant is never matched, so never listed here.
CREATE OR REPLACE VIEW strata.ops.supplier_review_list AS
SELECT
  p.pair_id,
  p.left_key,
  p.left_name,
  p.left_country,
  p.left_contracts,
  p.right_key,
  p.right_name,
  p.right_country,
  p.right_contracts,
  p.match_probability,
  p.review_reason,
  p.model_decision,
  p.model_confidence,
  p.model_reason,
  p.matched_at,
  p.public_from
FROM strata.ops.supplier_pairs AS p
WHERE p.outcome = 'waiting'
  AND p.run_id = (SELECT max_by(q.run_id, q.matched_at) FROM strata.ops.supplier_pairs AS q)
