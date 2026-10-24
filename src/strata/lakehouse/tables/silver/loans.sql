-- IDA credits (Finances One DS00001) and IBRD loans (DS00047), latest snapshot, typed: one row per
-- loan or credit from each fetched page. Gold reads the newest snapshot of each.
--
-- loan_number              as both datasets write it, normalized: IDA60290, IBRD89940
-- lender                   IDA, IBRD or TF, from the loan number
-- status                   the dataset's credit_status or loan_status, such as Disbursing&Repaying
-- original_principal_usd, disbursed_usd, undisbursed_usd, cancelled_usd   in US dollars
-- approval_date            board_approval_date
-- effective_date           effective_date_most_recent
-- closing_date             closed_date_most_recent
-- end_of_period            the month end the snapshot describes
-- approval_fiscal_year     the fiscal year of approval_date, July to June
-- fiscal_year              the fiscal year of end_of_period
-- public_from              end_of_period, or the fetch day when it is later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.loans (
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
