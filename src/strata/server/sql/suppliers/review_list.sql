-- The review list for suppliers: each candidate pair of name matching that waits for a person, with both
-- sides' names, countries and contracts (strata.ops.supplier_review_list), most likely first.
SELECT
  pair_id,
  left_key,
  left_name,
  left_country,
  left_contracts,
  right_key,
  right_name,
  right_country,
  right_contracts,
  match_probability,
  review_reason,
  model_decision,
  model_confidence,
  model_reason
FROM strata.ops.supplier_review_list
ORDER BY match_probability DESC, pair_id
