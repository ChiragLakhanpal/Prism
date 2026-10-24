-- Each supplier of each contract: one row per joint-venture member, which links the joint venture
-- to its members. A member's share is never added to the contract's amount again: that is
-- gold.contract.contract_amount_usd.
--
-- contract_id                    the contract, as gold.contract keys it
-- wb_contract_number             the awards datasets' contract number; empty for a contract known
--                                from its award notice
-- supplier_id                    the member's supplier ID (gold.supplier): its STEP supplier ID, or
--                                the supplier its name resolved to (ticket 19)
-- joint_venture_id               the joint venture it belongs to on this contract; empty when it signed alone
-- supplier_contract_amount_usd   the member's share, as the awards since FY2020 give it; empty for
--                                the FY2001 to FY2016 awards and award notices, which give none
-- public_from                    the contract's public_from (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.contract_supplier (
  contract_id STRING NOT NULL,
  wb_contract_number STRING,
  supplier_id STRING NOT NULL,
  joint_venture_id STRING,
  supplier_contract_amount_usd DECIMAL(18, 2),
  public_from DATE NOT NULL
)
