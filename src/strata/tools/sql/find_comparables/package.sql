-- find_comparables: the package's row in the newest plan version that lists it and was public on the
-- as-of date (ADR 0002), in STEP's columns, with that version's planned dates for the specific
-- procurement notice and the signed contract, and the project and country it belongs to.
--
-- A package is named by its STEP reference. When several versions list it, the newest by plan date
-- wins, then the one disclosed last; within a version, the first page that lists it. reference_repair says when
-- the reference breaks STEP's grammar and stays as the plan gives it (reference_as_read; ticket 131).
SELECT
  r.activity_reference_no,
  r.reference_repair,
  r.document_id,
  r.project_id,
  r.section,
  r.description,
  r.review_type,
  r.method,
  r.market_approach,
  r.estimated_amount_usd,
  r.process_status,
  r.pdf_page,
  r.public_from,
  v.implementing_agency,
  v.plan_date,
  v.disclosed_on,
  n.planned_on AS planned_notice_on,
  s.planned_on AS planned_signing_on,
  p.project_name,
  p.country_code,
  c.country_name
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
LEFT JOIN strata.silver.plan_steps AS n
  ON n.document_id = r.document_id
  AND n.activity_reference_no = r.activity_reference_no
  AND n.step = 'Specific Procurement Notice / Invitation'
LEFT JOIN strata.silver.plan_steps AS s
  ON s.document_id = r.document_id
  AND s.activity_reference_no = r.activity_reference_no
  AND s.step = 'Signed Contract'
LEFT JOIN strata.gold.project AS p ON p.project_id = r.project_id AND p.public_from <= :as_of
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE r.activity_reference_no = :step_reference
  AND v.public_from <= :as_of
ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page
LIMIT 1
