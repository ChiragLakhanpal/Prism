-- The judgements the model gave the last run, which the next run keeps while the judge and both
-- names are the same, so the model is not asked about a pair again every night.
SELECT pair_id, left_name, right_name, model, model_decision, model_confidence, model_reason
FROM strata.ops.supplier_pairs
WHERE model_decision IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY pair_id ORDER BY matched_at DESC) = 1
