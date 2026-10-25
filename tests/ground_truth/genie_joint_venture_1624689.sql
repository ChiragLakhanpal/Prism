-- Genie's question genie-joint-venture-1624689 (evals/benchmark.yaml): the two firms that signed contract 1624689
-- together, by STEP supplier ID, and each one's share. tests/ground_truth/values.toml's [awkward.joint_venture]:
-- supplier_ids 503708 and 503711, with the contract amount split equally, 697,972.33 US dollars each. It is one
-- published contract, so the workspace returns the same rows. Run it there with:
-- uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- expect: supplier_id,supplier_contract_amount_usd
-- expect: 503708,697972.33
-- expect: 503711,697972.33
SELECT supplier_id, supplier_contract_amount_usd
FROM strata.gold.contract_supplier
WHERE wb_contract_number = '1624689'
ORDER BY supplier_id
