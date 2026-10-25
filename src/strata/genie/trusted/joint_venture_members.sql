-- Trusted SQL for the Genie space (config/genie.toml): the members of each joint venture and each one's share of
-- its contract in US dollars. A supplier is named by its STEP supplier ID, never by a person's name.
SELECT wb_contract_number, supplier_id, supplier_contract_amount_usd
FROM strata.gold.contract_supplier
WHERE joint_venture_id IS NOT NULL
ORDER BY wb_contract_number, supplier_id
