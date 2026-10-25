-- project_signals: the plan version that first lists each of the project's activities, public by the
-- as-of date, with that version's date and the same agency's version before it. An activity whose first
-- listing has no version before it may only look new because its agency's earliest plan is the first one
-- read, so the late direct selection check leaves it out.
SELECT
  l.activity_reference_no,
  l.document_id,
  v.plan_date,
  v.previous_document_id,
  l.public_from
FROM strata.silver.plan_listings AS l
JOIN strata.silver.plan_versions AS v ON v.document_id = l.document_id
WHERE l.project_id = :project_id
  AND l.is_first_listing
  AND l.public_from <= :as_of
