-- The one box's activity lookup (ticket 14): the latest Procurement Plan public by the as-of date that
-- lists this STEP reference, with whether it is still its agency's latest plan on that date, so the box
-- can open that plan's check with the row in view.
SELECT
  v.project_id,
  v.implementing_agency,
  v.plan_date,
  (
    SELECT max(w.plan_date)
    FROM strata.silver.plan_versions AS w
    WHERE w.project_id = v.project_id
      AND w.implementing_agency = v.implementing_agency
      AND w.public_from <= :as_of
  ) AS latest_plan_date
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE r.activity_reference_no = :reference
  AND r.public_from <= :as_of
  AND v.public_from <= :as_of
ORDER BY v.plan_date DESC, v.public_from DESC, v.document_id DESC
LIMIT 1
