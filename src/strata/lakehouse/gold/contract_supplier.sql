-- strata.gold.contract_supplier: each supplier row of each contract, as the newest fetch of the
-- contract holds them (strata.silver.awards_current), linked to the contract's joint venture when
-- it has several members.
-- key: wb_contract_number, supplier_id
SELECT
  l.wb_contract_number,
  l.supplier_id,
  CASE WHEN c.joint_venture THEN c.supplier_id END AS joint_venture_id,
  l.supplier_contract_amount_usd,
  c.public_from
FROM strata.silver.awards_current AS l
JOIN strata.gold.contract AS c ON c.wb_contract_number = l.wb_contract_number
WHERE l.supplier_id IS NOT NULL
