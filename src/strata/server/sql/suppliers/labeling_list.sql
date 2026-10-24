-- The labeling tool's next pairs: candidate pairs of the latest run of name matching with no label yet,
-- most likely first, so the pairs auto-merge decides are labeled early. It gives only what a person needs
-- to judge the pair, and not where Strata sent it, so a label is not swayed by Strata's own decision.
SELECT
  p.pair_id,
  p.left_key,
  p.left_name,
  p.left_country,
  p.left_contracts,
  p.right_key,
  p.right_name,
  p.right_country,
  p.right_contracts
FROM strata.ops.supplier_pairs AS p
WHERE p.run_id = (SELECT max_by(q.run_id, q.matched_at) FROM strata.ops.supplier_pairs AS q)
  AND NOT EXISTS (SELECT 1 FROM strata.ops.supplier_pair_labels AS l WHERE l.pair_id = p.pair_id)
QUALIFY row_number() OVER (ORDER BY p.match_probability DESC, p.pair_id) <= :limit
ORDER BY p.match_probability DESC, p.pair_id
