-- A contract: a signed award to a supplier (GLOSSARY.md), one row per wb_contract_number. A joint
-- venture's members share one contract, so contract_amount_usd adds their shares and counts the
-- contract's amount once.
--
-- step_reference         the package it belongs to, when the dataset carries a STEP reference
-- reference_method_code  the method part of the reference, kept for the data note only
-- supplier_id            the contract's supplier: the member, or the joint venture (JV-...) when
--                        it has several members, which gold.contract_supplier lists
-- supplier_count         how many supplier rows the dataset gives for the contract
-- joint_venture          true when it has more than one supplier
-- public_from            contract_signing_date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.contract (
  wb_contract_number STRING NOT NULL,
  project_id STRING,
  country_code STRING,
  step_reference STRING,
  reference_method_code STRING,
  borrower_contract_reference_number STRING,
  contract_description STRING,
  procurement_category STRING,
  procurement_method STRING,
  review_type STRING,
  contract_signing_date DATE,
  fiscal_year INT,
  contract_amount_usd DECIMAL(18, 2),
  supplier_id STRING,
  supplier_count INT NOT NULL,
  joint_venture BOOLEAN NOT NULL,
  public_from DATE NOT NULL
)
