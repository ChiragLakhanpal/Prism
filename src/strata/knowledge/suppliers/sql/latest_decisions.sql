-- The latest decision a person made on each candidate pair of name matching for suppliers. It
-- outranks the thresholds and the model (strata.knowledge.suppliers.resolve) while the pair's two names
-- are still the ones the person saw.
SELECT pair_id, decision, reviewer, reason, left_name, right_name
FROM strata.ops.supplier_review_decisions
QUALIFY row_number() OVER (PARTITION BY pair_id ORDER BY decided_at DESC) = 1
