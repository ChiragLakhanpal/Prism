-- How many candidate pairs the latest run of name matching found, and how many of them carry a label given
-- to the pair's two names.
SELECT
  count(*) AS candidate_pairs,
  count(CASE WHEN EXISTS (SELECT 1 FROM strata.ops.supplier_pair_labels AS l
                          WHERE l.pair_id = p.pair_id AND l.left_name = p.left_name AND l.right_name = p.right_name)
             THEN 1 END) AS labeled_pairs
FROM strata.ops.supplier_pairs AS p
WHERE p.run_id = (SELECT max_by(q.run_id, q.matched_at) FROM strata.ops.supplier_pairs AS q)
