-- strata.gold.contract_supplier: each supplier of each contract, linked to the contract's joint
-- venture when it has several members.
--   awards     each supplier row of each contract, as the newest fetch of the contract holds them
--              (strata.silver.awards_current), with the member's share
--   resolved   each supplier of a contract from the FY2001 to FY2016 awards or from an award notice,
--              as supplier resolution found it (strata.silver.supplier_resolution, ticket 19). Neither
--              gives a member's share, so it is empty; the contract's amount is gold.contract's.
-- key: contract_id, supplier_id
WITH awards AS (
  SELECT
    c.contract_id,
    l.wb_contract_number,
    l.supplier_id,
    CASE WHEN c.joint_venture THEN c.supplier_id END AS joint_venture_id,
    l.supplier_contract_amount_usd,
    c.public_from
  FROM strata.silver.awards_current AS l
  JOIN strata.gold.contract AS c ON c.wb_contract_number = l.wb_contract_number AND c.source = 'awards'
  WHERE l.supplier_id IS NOT NULL
),
resolved AS (
  SELECT
    c.contract_id,
    c.wb_contract_number,
    r.supplier_id,
    min(r.joint_venture_id) AS joint_venture_id,
    CAST(NULL AS DECIMAL(18, 2)) AS supplier_contract_amount_usd,
    min(c.public_from) AS public_from
  FROM strata.silver.supplier_resolution AS r
  JOIN strata.gold.contract AS c ON c.contract_id = r.contract_id AND c.source = r.source
  WHERE r.supplier_id IS NOT NULL
  GROUP BY c.contract_id, c.wb_contract_number, r.supplier_id
)
SELECT * FROM awards
UNION ALL
SELECT * FROM resolved
