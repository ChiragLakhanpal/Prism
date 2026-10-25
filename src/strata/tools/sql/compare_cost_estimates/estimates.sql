-- compare_cost_estimates: each package's cost estimate, the one rule that chooses it (CLAUDE.md rule 4). A package
-- can have several plan rows with different Estimated Amounts, one per version of its Procurement Plan. The
-- cost estimate is the Estimated Amount (US$) of the first version, by plan date, that lists the package with
-- one, among the versions public on the as-of date (ADR 0002): the cost estimate as first published, as delay
-- is measured from the first published planned date. Of two versions with the same date, the one disclosed
-- first; within a version, the first page that lists it.
SELECT
  r.activity_reference_no AS step_reference,
  r.estimated_amount_usd,
  r.document_id,
  r.pdf_page,
  v.plan_date,
  v.implementing_agency,
  v.public_from
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE array_contains(split(:refs, ','), r.activity_reference_no)
  AND r.estimated_amount_usd IS NOT NULL
  AND v.public_from <= :as_of
QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                           ORDER BY v.plan_date, v.public_from, r.document_id, r.pdf_page) = 1
