-- A package: one planned procurement, keyed by its STEP reference (GLOSSARY.md), from its notices
-- and its contracts, with the Process Status of the newest Procurement Plan that lists it
-- (silver.plan_rows). The plan's planned dates are in silver.plan_steps and plan_step_delays.
--
-- procurement_category      from the first specific procurement notice's group, else the contract's
-- procurement_method        the contract's method, else the notice's, never the reference's
-- reference_method_code     the method part of the reference, kept for the data note only
-- first_notice_id, _type, _date   the first specific procurement notice (not a General Procurement
--                           Notice or a Contract Award), where procurement cycle time starts
-- bids_due                  that notice's submission deadline
-- contract_signed_on        the earliest signing date in the awards dataset, else the Contract
--                           Signature Date of its Contract Award notice
-- signed_in                 contract awards, or award notice, for where contract_signed_on came from
-- award_notice_id           its first Contract Award notice that gives a signature date
-- contract_count            its contracts in the awards dataset
-- review_type               Prior or Post, from its contracts
-- process_status            Process Status, word for word, in the newest plan version that lists
--                           it, such as Canceled or Signed; empty when no plan read so far lists it
-- process_status_document_id   that plan version (silver.plan_versions), which a claim cites
-- process_status_public_from   that plan version's public date (ADR 0002)
-- public_from               the earliest public_from of its notices and contracts (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.package (
  step_reference STRING NOT NULL,
  project_id STRING,
  country_code STRING,
  procurement_category STRING,
  procurement_method STRING,
  reference_method_code STRING,
  first_notice_id STRING,
  first_notice_type STRING,
  first_notice_date DATE,
  bids_due DATE,
  contract_signed_on DATE,
  signed_in STRING,
  award_notice_id STRING,
  contract_count INT NOT NULL,
  review_type STRING,
  process_status STRING,
  process_status_document_id STRING,
  process_status_public_from DATE,
  public_from DATE NOT NULL
)
