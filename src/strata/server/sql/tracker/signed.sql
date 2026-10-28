-- The step tracker (ticket 115): the first signing of a contract for one package (its STEP reference), from
-- strata.gold.contract, among the contracts public by the as-of date and signed by then (ADR 0002). source names the
-- record: the contract awards datasets (awards, awards_fy2001_2016) or an award notice (notices). The tracker marks
-- the plan's Signed Contract step done on this date when the plan gives the step no actual date.
SELECT c.contract_signing_date AS signed_on, c.source
FROM strata.gold.contract AS c
WHERE c.step_reference = :reference
  AND c.public_from <= :as_of
  AND c.contract_signing_date <= :as_of
ORDER BY c.contract_signing_date, c.contract_id
LIMIT 1
