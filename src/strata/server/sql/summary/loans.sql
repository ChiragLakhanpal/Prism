-- A project's Summary: each of its loans and credits in their newest monthly snapshot, public by the
-- as-of date, with what each committed, disbursed and canceled.
SELECT
  loan_number,
  original_principal_usd,
  disbursed_usd,
  cancelled_usd,
  as_of,
  public_from
FROM strata.gold.loan
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY loan_number
