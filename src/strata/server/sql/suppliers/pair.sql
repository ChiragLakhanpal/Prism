-- One candidate pair of the latest run of name matching, by its pair_id.
SELECT p.pair_id, p.left_key, p.right_key
FROM strata.ops.supplier_pairs AS p
WHERE p.pair_id = :pair_id
  AND p.run_id = (SELECT max_by(q.run_id, q.matched_at) FROM strata.ops.supplier_pairs AS q)
