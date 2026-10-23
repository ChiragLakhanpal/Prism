-- strata.gold.contract_supplier: each supplier row of each contract, linked to the contract's joint
-- venture when it has several members.
-- key: wb_contract_number, supplier_id
WITH latest AS (
  SELECT *
  FROM strata.silver.awards
  WHERE supplier_id IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY wb_contract_number, supplier_id ORDER BY fetched_at DESC, page_hash) = 1
)
SELECT
  l.wb_contract_number,
  l.supplier_id,
  CASE WHEN c.joint_venture THEN c.supplier_id END AS joint_venture_id,
  l.supplier_contract_amount_usd,
  c.public_from
FROM latest AS l
JOIN strata.gold.contract AS c ON c.wb_contract_number = l.wb_contract_number
