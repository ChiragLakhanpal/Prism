-- Genie's question genie-award-notice-contracts-fy2017-2019 (evals/benchmark.yaml): the contracts signed in fiscal
-- 2017 to 2019, which neither awards dataset covers, that only a Contract Award notice records, by fiscal year.
-- The counts are tests/ground_truth/values.toml's [counts.gap_years], read from the notices by hand: two in fiscal
-- 2017, one in fiscal 2018 and four in fiscal 2019. The workspace holds every country's notices, so the full gate
-- compares Genie's rows with this query's on the SQL warehouse; it is not marked for same-rows.
-- expect: fiscal_year,contracts
-- expect: 2017,2
-- expect: 2018,1
-- expect: 2019,4
SELECT fiscal_year, count(*) AS contracts
FROM strata.gold.contract
WHERE source = 'notices' AND fiscal_year BETWEEN 2017 AND 2019
GROUP BY fiscal_year
ORDER BY fiscal_year
