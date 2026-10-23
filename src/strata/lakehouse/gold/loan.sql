-- strata.gold.loan: each loan or credit from its newest snapshot: the latest month end, then the
-- latest fetch.
-- key: loan_number
SELECT
  loan_number,
  lender,
  project_id,
  country_code,
  status,
  original_principal_usd,
  disbursed_usd,
  undisbursed_usd,
  cancelled_usd,
  approval_date,
  effective_date,
  closing_date,
  end_of_period AS as_of,
  public_from
FROM strata.silver.loans
QUALIFY row_number() OVER (PARTITION BY loan_number ORDER BY end_of_period DESC, fetched_at DESC, page_hash) = 1
