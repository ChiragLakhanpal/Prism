-- A procurement notice, from the newest page that held it. Contact details were removed before
-- the page was kept (CLAUDE.md rule 8).
--
-- step_reference                 the STEP reference, normalized, when bid_reference_no is one
-- reference_method_code          the method part of the reference, kept for the data note only
-- procurement_method             the current Procurement Regulations' name
-- procurement_method_code, procurement_method_as_written   the notice's own words, such as ICB
-- market_approach                what an old method name says, in STEP's words
-- loan_number                    IDA60300; a bare number is matched to the loans of the notice's project
-- contract_signature_date        a Contract Award notice's Contract Signature Date
-- contract_fiscal_year           its contract's fiscal year, from that date, or the notice date when it gives none
-- signed_contract_price, signed_contract_currency   a Contract Award notice's signed price, in its own currency
-- public_from                    the notice date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.notice (
  notice_id STRING NOT NULL,
  notice_type STRING,
  notice_date DATE,
  notice_status STRING,
  project_id STRING,
  country_code STRING,
  step_reference STRING,
  reference_method_code STRING,
  bid_reference_no STRING,
  bid_description STRING,
  procurement_category STRING,
  procurement_method STRING,
  procurement_method_code STRING,
  procurement_method_as_written STRING,
  market_approach STRING,
  submission_deadline DATE,
  loan_number STRING,
  contract_signature_date DATE,
  contract_fiscal_year INT,
  signed_contract_price DECIMAL(20, 2),
  signed_contract_currency STRING,
  public_from DATE NOT NULL
)
