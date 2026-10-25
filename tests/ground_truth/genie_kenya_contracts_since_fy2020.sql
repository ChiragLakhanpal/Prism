-- Genie's question genie-kenya-contracts-since-fy2020 (evals/benchmark.yaml): Kenya's contracts in the contract
-- awards since fiscal 2020, and how many carry a STEP reference. Plain SQL over the gold tables, written apart
-- from the Genie space's trusted SQL, so it checks the SQL Genie writes. The counts are tests/ground_truth/
-- values.toml's [counts.kenya] (contracts = 603, with_step_reference = 528), counted from the recorded award files.
-- The workspace holds every Kenya project's awards, not the fixture's three, so the full gate runs this query on
-- the SQL warehouse and compares Genie's rows with what it returns there; it is not marked for same-rows.
-- expect: contracts,with_step_reference
-- expect: 603,528
SELECT count(*) AS contracts, count(step_reference) AS with_step_reference
FROM strata.gold.contract
WHERE country_code = 'KE' AND source = 'awards'
