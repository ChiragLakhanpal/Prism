-- Genie's question genie-contract-ke-nwwda-229129 (evals/benchmark.yaml): when KE-NWWDA-229129-CW-RFB's contract
-- was signed and its amount in US dollars. tests/ground_truth/values.toml: award-229129-signed (January 3, 2022)
-- and plan-229129-actual (1,245,092.76). It is one published contract, so the workspace returns the same row.
-- Run it there with: uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- expect: contract_signing_date,contract_amount_usd
-- expect: 2022-01-03,1245092.76
SELECT contract_signing_date, contract_amount_usd
FROM strata.gold.contract
WHERE step_reference = 'KE-NWWDA-229129-CW-RFB'
