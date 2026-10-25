-- find_comparables: one contract award's fields, as the evidence drawer's contract card shows a comparable's
-- first contract, if it was public on the as-of date (ADR 0002). No supplier is named: an individual
-- consultant never is, and the card says how many suppliers signed instead.
SELECT
  c.contract_id,
  c.wb_contract_number,
  c.contract_description,
  c.procurement_method,
  c.market_approach,
  c.review_type,
  c.contract_signing_date,
  c.contract_amount_usd,
  c.supplier_count,
  c.joint_venture,
  c.public_from
FROM strata.gold.contract AS c
WHERE c.contract_id = :contract_id
  AND c.public_from <= :as_of
