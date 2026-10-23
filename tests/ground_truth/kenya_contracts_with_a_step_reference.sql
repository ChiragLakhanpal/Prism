-- Kenya's contracts in the fixture, and how many carry a STEP reference, in the run's data readiness
-- measure and in gold.
--
-- Counted by hand from the recorded award files (api/awards/P156634.json and
-- api/awards/P176758-P170941.json), apart from Strata's code: 603 distinct wb_contract_number
-- values, of which 528 have a borrower_contract_reference_number shaped like a STEP reference
-- (two letters, an agency, digits, CW, GO, CS or NC, and a method, separated by hyphens, or by the
-- slashes and stray spaces some rows use).
-- expect: counted_in,with_step_reference,contracts
-- expect: gold,528,603
-- expect: ops,528,603
SELECT 'gold' AS counted_in, count(step_reference) AS with_step_reference, count(*) AS contracts
FROM strata.gold.contract
WHERE country_code = 'KE'
UNION ALL
SELECT 'ops', numerator, denominator
FROM strata.ops.data_readiness
WHERE run_id = 'fixture' AND source = 'awards' AND measure = 'linked_step_reference' AND country_code = 'KE'
ORDER BY counted_in
