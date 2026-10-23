-- The monthly history of IDA credits (Finances One DS00976) and IBRD loans (DS00975) for the
-- slice's countries, typed: one row per loan or credit per month end from each fetched page, in
-- the same columns as strata.silver.loans.
--
-- end_of_period            the month end this row describes
-- fiscal_year              the fiscal year of end_of_period, July to June
-- closing_date             the closing date as that month reported it (closed_date_most_recent)
-- public_from              end_of_period, or the fetch day when it is later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.loan_history (
  loan_number STRING NOT NULL,
  lender STRING,
  project_id STRING,
  project_name STRING,
  country_code STRING,
  country STRING,
  borrower STRING,
  status STRING,
  original_principal_usd DECIMAL(18, 2),
  disbursed_usd DECIMAL(18, 2),
  undisbursed_usd DECIMAL(18, 2),
  cancelled_usd DECIMAL(18, 2),
  approval_date DATE,
  effective_date DATE,
  closing_date DATE,
  last_disbursement_date DATE,
  end_of_period DATE,
  approval_fiscal_year INT,
  fiscal_year INT,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
