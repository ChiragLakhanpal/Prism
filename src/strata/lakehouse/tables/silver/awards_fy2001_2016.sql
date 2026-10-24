-- Contract awards from FY2001 to FY2016 (Finances One DS01004), typed and cleaned: one row per row
-- of the dataset, which holds prior-review contracts only and has not changed since March 2022.
-- Amounts are in US dollars. Each fetch of a page adds its rows; gold reads the newest.
--
-- The dataset's own field names are kept where the value is the same: contract_number,
-- borrower_contract_reference_number (free text, rarely a STEP reference), contract_signing_date.
-- step_reference                 the STEP reference, when the free-text reference happens to be one
-- reference_method_code          the method part of that reference, kept for the data note only
-- procurement_category           in STEP's words: the dataset's Civil Works is Works
-- procurement_method             the current Procurement Regulations' name, such as Request for Bids
-- procurement_method_as_written  the dataset's own words, such as International Competitive Bidding
-- market_approach                what the old name says, in STEP's words: ICB is Open - International
-- contract_description           the dataset's description; empty for a contract with a person
-- supplier                       the supplier as the dataset names it; empty for a contract with a person
-- individual_consultant          true for a contract with a person: an Individual Consultant Selection,
--                                an INDIVIDUAL CONSULTANT supplier, or Consultant Services whose
--                                description gives a personal title and a name, so no person is named
-- supplier_contract_amount_usd   the dataset's supplier_contract_amount, in US dollars
-- fiscal_year                    July to June, worked out from contract_signing_date
-- page_hash, fetched_at          the bronze page the row came from
-- public_from                    contract_signing_date: the dataset gives no publication date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.awards_fy2001_2016 (
  contract_number STRING NOT NULL,
  project_id STRING,
  project_name STRING,
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
  supplier STRING,
  individual_consultant BOOLEAN NOT NULL,
  supplier_country STRING,
  supplier_contract_amount_usd DECIMAL(18, 2),
  contract_signing_date DATE,
  fiscal_year INT,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
