-- A loan or credit, from its newest snapshot (strata.silver.loans): the latest disbursed and
-- canceled amounts and closing date. gold.project_closing_date holds how the closing date moved.
--
-- loan_number              IDA60290 or IBRD89940, as gold.project_loan and gold.notice write it
-- lender                   IDA, IBRD or TF
-- status                   such as Disbursing&Repaying, word for word
-- original_principal_usd, disbursed_usd, undisbursed_usd, cancelled_usd   in US dollars
-- closing_date             the most recent closing date
-- as_of                    the month end of the snapshot
-- public_from              as_of (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.loan (
  loan_number STRING NOT NULL,
  lender STRING,
  project_id STRING,
  country_code STRING,
  status STRING,
  original_principal_usd DECIMAL(18, 2),
  disbursed_usd DECIMAL(18, 2),
  undisbursed_usd DECIMAL(18, 2),
  cancelled_usd DECIMAL(18, 2),
  approval_date DATE,
  effective_date DATE,
  closing_date DATE,
  as_of DATE,
  public_from DATE NOT NULL
)
