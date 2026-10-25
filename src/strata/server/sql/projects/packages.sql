-- A project's Packages (the 21 brief, section 4.1): every activity in each implementing agency's latest
-- Procurement Plan whose STEP tables the layout parser read, public by the as-of date. Agencies come with
-- the newest plan first, then each plan's rows in the order of its tables.
WITH read_versions AS (
  SELECT
    v.document_id,
    v.implementing_agency,
    v.plan_date,
    v.public_from
  FROM strata.silver.plan_versions AS v
  WHERE v.project_id = :project_id
    AND v.public_from <= :as_of
    AND v.implementing_agency IS NOT NULL
    AND EXISTS (SELECT 1 FROM strata.silver.plan_rows AS r WHERE r.document_id = v.document_id)
),
latest AS (
  SELECT *
  FROM read_versions
  QUALIFY row_number() OVER (PARTITION BY implementing_agency ORDER BY plan_date DESC, public_from DESC,
                                                                        document_id DESC) = 1
)
SELECT
  l.implementing_agency,
  l.plan_date,
  r.activity_reference_no,
  r.description,
  r.method,
  r.market_approach,
  r.estimated_amount_usd,
  r.process_status
FROM latest AS l
JOIN strata.silver.plan_rows AS r ON r.document_id = l.document_id
ORDER BY
  l.plan_date DESC,
  l.implementing_agency,
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
