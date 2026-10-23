-- Procurement notices, typed and cleaned: one row per notice from each fetched page. Gold reads the
-- newest row for each notice. Contact names, addresses, emails, phone numbers and web addresses
-- never reach this table: the fetch removes them before a page is kept in bronze (CLAUDE.md rule 8).
--
-- bid_reference_no                the reference as the notice writes it
-- step_reference                  the STEP reference, normalized, when the reference is one
-- reference_method_code           the method part of the reference, kept for the data note only
-- procurement_group               the notice's group as written: CW, GO, CS or NC
-- procurement_category            Works, Goods, Consultant Services or Non-consulting Services
-- procurement_method_code         the method's code as the notice writes it, such as ICB
-- procurement_method_as_written   the method's name as the notice writes it
-- procurement_method              the current Procurement Regulations' name, such as Request for Bids
-- market_approach                 what an old method name says, in STEP's words: ICB is Open - International
-- loan_number                     IDA60300, when the notice writes the lender; empty for a bare number
-- loan_digits                     the loan or credit number's digits, which gold matches to the project's loans
-- contract_signature_date         a Contract Award notice's Contract Signature Date
-- signed_contract_price, _currency  a Contract Award notice's signed price, in the currency it names
-- notice_text                     the notice as plain text
-- contact_details_removed         true when the fetch removed any contact detail from the notice
-- public_from                     the notice date, or the fetch day when it is missing or later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.notices (
  notice_id STRING NOT NULL,
  notice_type STRING,
  notice_date DATE,
  notice_status STRING,
  notice_language STRING,
  project_id STRING,
  project_name STRING,
  project_country STRING,
  bid_reference_no STRING,
  step_reference STRING,
  reference_method_code STRING,
  bid_description STRING,
  procurement_group STRING,
  procurement_category STRING,
  procurement_method_code STRING,
  procurement_method_as_written STRING,
  procurement_method STRING,
  market_approach STRING,
  submission_deadline DATE,
  loan_number_as_written STRING,
  loan_number STRING,
  loan_digits STRING,
  contract_signature_date DATE,
  signed_contract_price DECIMAL(20, 2),
  signed_contract_currency STRING,
  notice_text STRING,
  contact_details_removed BOOLEAN NOT NULL,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
