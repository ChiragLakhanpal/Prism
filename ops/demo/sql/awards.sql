-- The demo-ready command's recheck (ticket 48; ops/demo/ready.py): the contracts the awards datasets, or an
-- award notice, hold for one STEP reference, public by the as-of date (ADR 0002). The command asks it for each
-- activity whose row in the demo plan shows no signed contract, and lists the two records side by side when they
-- disagree (data/fixture/README.md, "Before demo day"). It decides nothing about which one is right.
SELECT
  contract_id,
  source,
  contract_signing_date,
  contract_amount_usd
FROM strata.gold.contract
WHERE step_reference = :step_reference
  AND public_from <= :as_of
ORDER BY contract_signing_date, contract_id
