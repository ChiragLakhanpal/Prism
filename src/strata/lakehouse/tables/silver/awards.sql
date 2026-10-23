-- Contract awards since FY2020 (Finances One DS00005), typed and cleaned: one row per supplier of
-- each contract, as the dataset gives them, so a joint venture has one row per member. Each fetch
-- of a page adds its rows; gold reads the newest row for each contract and supplier.
--
-- The dataset's own field names are kept where the value is the same: wb_contract_number,
-- borrower_contract_reference_number (as written), contract_signing_date, fiscal_year and
-- supplier_contract_amount_usd, the member's share in US dollars.
-- step_reference            the STEP reference, normalized, when the reference is one
-- reference_method_code     the method part of the reference, kept for the data note, never the method
-- procurement_method        the current Procurement Regulations' name
-- procurement_method_as_written  the dataset's own words, kept when an old name was mapped
-- market_approach           what an old method name says, in STEP's words, such as Open - National
-- supplier                  the supplier's name; empty for an individual consultant
-- individual_consultant     true when the dataset names the supplier only as INDIVIDUAL CONSULTANT
-- fiscal_year               July to June, worked out from contract_signing_date
-- page_hash, fetched_at     the bronze page the row came from
-- public_from               contract_signing_date: the dataset gives no publication date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.awards (
  wb_contract_number STRING NOT NULL,
  supplier_id STRING,
  project_id STRING,
  project_name STRING,
  borrower_country_code STRING,
  borrower_country STRING,
  region STRING,
  global_practice STRING,
  borrower_contract_reference_number STRING,
  step_reference STRING,
  reference_method_code STRING,
  contract_description STRING,
  procurement_category STRING,
  procurement_method STRING,
  procurement_method_as_written STRING,
  market_approach STRING,
  review_type STRING,
  supplier STRING,
  individual_consultant BOOLEAN NOT NULL,
  supplier_country STRING,
  supplier_country_code STRING,
  supplier_contract_amount_usd DECIMAL(18, 2),
  contract_signing_date DATE,
  fiscal_year INT,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
