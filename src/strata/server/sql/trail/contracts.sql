-- The contract trail's contracts (ticket 22): every contract that carries the STEP reference, in signing order,
-- with its supplier as gold.supplier names it (never named for an individual consultant, and a joint venture
-- with its members' names) and whether it was public on the as-of date (ADR 0002). No column scores, ranks or
-- profiles a supplier.
SELECT
  c.contract_id,
  c.source,
  c.wb_contract_number,
  c.award_notice_id,
  c.project_id,
  c.step_reference,
  c.contract_description,
  c.procurement_category,
  c.procurement_method,
  c.review_type,
  c.contract_signing_date,
  c.contract_amount_usd,
  c.contract_amount,
  c.contract_currency,
  c.joint_venture,
  s.name AS supplier_name,
  s.country AS supplier_country,
  s.kind AS supplier_kind,
  c.public_from,
  c.public_from <= :as_of AS public_then
FROM strata.gold.contract AS c
LEFT JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id
WHERE c.step_reference = :reference
ORDER BY c.contract_signing_date, c.contract_id
