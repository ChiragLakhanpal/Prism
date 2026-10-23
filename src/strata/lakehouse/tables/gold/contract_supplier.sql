-- Each supplier of each contract: one row per joint-venture member, which links the joint venture
-- to its members. A member's share is never added to the contract's amount again: that is
-- gold.contract.contract_amount_usd.
--
-- supplier_id                    the member's STEP supplier ID
-- joint_venture_id               the joint venture it belongs to on this contract; empty when it signed alone
-- supplier_contract_amount_usd   the member's share, as the awards dataset gives it
-- public_from                    the contract's signing date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.contract_supplier (
  wb_contract_number STRING NOT NULL,
  supplier_id STRING NOT NULL,
  joint_venture_id STRING,
  supplier_contract_amount_usd DECIMAL(18, 2),
  public_from DATE NOT NULL
)
