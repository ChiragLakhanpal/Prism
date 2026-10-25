-- One contract by its id, as the evidence drawer shows it from the contract trail (ticket 22), where it was public
-- on the as-of date (ADR 0002), with its supplier as gold.supplier names it (never an individual consultant).
SELECT
  c.contract_id,
  c.source,
  c.wb_contract_number,
  c.award_notice_id,
  c.project_id,
  c.step_reference,
  c.contract_description,
  c.procurement_method,
  c.review_type,
  c.contract_signing_date,
  c.contract_amount_usd,
  c.contract_amount,
  c.contract_currency,
  s.name AS supplier_name,
  s.country AS supplier_country,
  s.kind AS supplier_kind,
  c.public_from
FROM strata.gold.contract AS c
LEFT JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id
WHERE c.contract_id = :contract_id
  AND c.public_from <= :as_of
