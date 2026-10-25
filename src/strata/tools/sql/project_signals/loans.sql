-- project_signals: each of the project's loans and credits in its newest monthly snapshot (gold.loan),
-- public by the as-of date, with what each committed, disbursed, has left to disburse and canceled.
SELECT
  loan_number,
  original_principal_usd,
  disbursed_usd,
  undisbursed_usd,
  cancelled_usd,
  closing_date,
  as_of,
  public_from
FROM strata.gold.loan
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY loan_number
