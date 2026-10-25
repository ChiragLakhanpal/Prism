-- project_records: each activity's Estimated Amount (US$) in every plan version public by the as-of date that
-- lists it, so a contract can be shown beside the estimate of the latest plan that lists its STEP reference.
SELECT
  r.activity_reference_no,
  r.estimated_amount_usd,
  r.document_id,
  v.plan_date,
  r.public_from
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
ORDER BY r.activity_reference_no, v.plan_date
