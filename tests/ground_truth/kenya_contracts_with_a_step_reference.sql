-- Kenya's contracts in the fixture, and how many carry a STEP reference, in the run's data readiness
-- measure and in gold.
--
-- The expected counts are tests/ground_truth/values.toml's [counts.kenya], counted from the
-- recorded award files apart from Strata's code: 603 contracts (contracts = 603), of which 528
-- carry a STEP reference (with_step_reference = 528).
-- expect: counted_in,with_step_reference,contracts
-- expect: gold,528,603
-- expect: ops,528,603
SELECT 'gold' AS counted_in, count(step_reference) AS with_step_reference, count(*) AS contracts
FROM strata.gold.contract
WHERE country_code = 'KE'
UNION ALL
SELECT 'ops', count, denominator
FROM strata.ops.data_readiness
WHERE run_id = 'fixture' AND source = 'awards' AND measure = 'linked_step_reference' AND subject = 'KE'
ORDER BY counted_in
