-- A contract: a signed award to a supplier (GLOSSARY.md), one row per contract, from the awards
-- since FY2020, the awards from FY2001 to FY2016, or, for FY2017 to FY2019, which neither awards
-- dataset covers, an award notice. A joint venture's members share one contract, so
-- contract_amount_usd adds their shares and counts the contract's amount once.
--
-- contract_id            wb_contract_number for a contract from an awards dataset; the award
--                        notice's id (OP...) for a contract from an award notice
-- source                 awards, awards_fy2001_2016 or notices (config/sources.toml)
-- wb_contract_number     the awards datasets' contract number; empty for a contract from a notice
-- award_notice_id        the Contract Award notice a contract from a notice comes from
-- step_reference         the package it belongs to, when the source carries a STEP reference
-- reference_method_code  the method part of the reference, kept for the data note only
-- procurement_method     the current Procurement Regulations' name, such as Request for Bids
-- procurement_method_as_written  the source's own words, such as International Competitive Bidding
-- market_approach        what an old method name says, in STEP's words: ICB is Open - International
-- review_type            Prior or Post; every FY2001 to FY2016 award is Prior, as that dataset
--                        holds prior-review contracts only; empty for a contract from a notice
-- fiscal_year            July to June, from the signing date (for a notice with no signature
--                        date, from the notice date)
-- contract_amount_usd    in US dollars; empty for a contract from a notice, never converted
-- contract_amount, contract_currency   the amount in the currency the source gives it in
-- amount_basis           US dollars, or local currency, from award notices
-- supplier_id            the contract's supplier: the member, or the joint venture (JV-...) when
--                        it has several members, which gold.contract_supplier lists; empty for the
--                        FY2001 to FY2016 dataset and for notices, which give no STEP supplier ID
-- supplier_count         how many supplier rows the dataset gives for the contract; 0 for a notice
-- joint_venture          true when it has more than one supplier row
-- public_from            the signing date for an awards dataset; the notice date for a notice (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.contract (
  contract_id STRING NOT NULL,
  source STRING NOT NULL,
  wb_contract_number STRING,
  award_notice_id STRING,
  project_id STRING,
  country_code STRING,
  step_reference STRING,
  reference_method_code STRING,
  borrower_contract_reference_number STRING,
  contract_description STRING,
  procurement_category STRING,
  procurement_method STRING,
  procurement_method_as_written STRING,
  market_approach STRING,
  review_type STRING,
  contract_signing_date DATE,
  fiscal_year INT,
  contract_amount_usd DECIMAL(18, 2),
  contract_amount DECIMAL(20, 2),
  contract_currency STRING,
  amount_basis STRING NOT NULL,
  supplier_id STRING,
  supplier_count INT NOT NULL,
  joint_venture BOOLEAN NOT NULL,
  public_from DATE NOT NULL
)
