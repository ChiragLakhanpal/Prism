-- check_plan: each activity in one plan version, in STEP's columns, with the dates its checks need.
--
-- Signed Contract: the actual signing date in this version, and its first published planned date
-- and delay from silver.plan_step_delays, the one definition of delay. Contract Completion: the
-- first published planned date, or this version's own planned date when the first listing gives
-- none. Rows public after the as-of date are left out, so a delay measured from a plan not yet
-- public is not used (ADR 0002). public_from is the latest public date among the rows each
-- activity's values come from.
--
-- Activities come in the order of the plan's tables (works, goods, non-consulting services,
-- consulting firms, individual consultants), then by PDF page and reference.
SELECT
  r.activity_reference_no,
  r.section,
  r.description,
  r.review_type,
  r.method,
  r.market_approach,
  r.estimated_amount_usd,
  r.actual_amount_usd,
  r.process_status,
  r.pdf_page,
  sc.actual_on AS signed_on,
  sc.first_planned_on AS planned_signing_on,
  sc.first_planned_plan_date AS planned_signing_plan_date,
  sc.delay_days AS days_late,
  COALESCE(cc.first_planned_on, cc.planned_on) AS planned_completion_on,
  CASE WHEN cc.first_planned_on IS NOT NULL THEN cc.first_planned_plan_date
       WHEN cc.planned_on IS NOT NULL THEN v.plan_date END AS planned_completion_plan_date,
  fl.first_listing_confirmed,
  GREATEST(r.public_from, sc.public_from, cc.public_from, fl.public_from) AS public_from
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
LEFT JOIN strata.silver.plan_step_delays AS sc
  ON sc.document_id = r.document_id
  AND sc.activity_reference_no = r.activity_reference_no
  AND sc.step = 'Signed Contract'
  AND sc.public_from <= :as_of
LEFT JOIN strata.silver.plan_step_delays AS cc
  ON cc.document_id = r.document_id
  AND cc.activity_reference_no = r.activity_reference_no
  AND cc.step = 'Contract Completion'
  AND cc.public_from <= :as_of
LEFT JOIN strata.silver.plan_listings AS fl
  ON fl.project_id = r.project_id
  AND fl.activity_reference_no = r.activity_reference_no
  AND fl.is_first_listing
  AND fl.public_from <= :as_of
WHERE r.document_id = :document_id
  AND r.public_from <= :as_of
ORDER BY
  CASE r.section
    WHEN 'WORKS' THEN 1
    WHEN 'GOODS' THEN 2
    WHEN 'NON CONSULTING SERVICES' THEN 3
    WHEN 'CONSULTING FIRMS' THEN 4
    WHEN 'INDIVIDUAL CONSULTANTS' THEN 5
    ELSE 6
  END,
  r.pdf_page,
  r.activity_reference_no
