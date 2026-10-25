-- compare_cost_estimates: every contract the packages signed in the contract awards data, in US dollars, public on
-- the as-of date (ADR 0002). gold.contract keeps a joint venture's contract once, at its whole amount, so a
-- package's signed amount adds these rows and never the awards data's rows per member. A contract known only
-- from a Contract Award notice (source notices) gives its price in the notice's currency, and is left out.
SELECT step_reference, contract_id, contract_amount_usd, contract_signing_date, public_from
FROM strata.gold.contract
WHERE array_contains(split(:refs, ','), step_reference)
  AND source <> 'notices'
  AND contract_amount_usd IS NOT NULL
  AND public_from <= :as_of
ORDER BY step_reference, contract_signing_date, contract_id
