-- The rebidding models' features for every package advertised from :period_from (ticket 28), each as the package
-- stood when it was advertised (docs/PLAN.md section 7, the leakage traps): its row in the newest plan version
-- public on or before both its notice's date and the as-of date (ADR 0002), and its project's country and region.
-- A package no plan read so far lists keeps its notice's method and category, and nothing else. No Process
-- Status, Actual Amount, signed amount, later plan version or later notice is read.
WITH first_notice AS (
  SELECT notice_id, notice_date, step_reference, public_from
  FROM strata.gold.notice
  WHERE step_reference IS NOT NULL AND public_from <= :as_of
    AND notice_type NOT IN ('General Procurement Notice', 'Contract Award')
  QUALIFY row_number() OVER (PARTITION BY step_reference ORDER BY notice_date, notice_id) = 1
),
packages AS (
  SELECT f.step_reference, f.notice_date, f.public_from, p.project_id, p.country_code, p.procurement_category,
    p.procurement_method
  FROM first_notice AS f
  JOIN strata.gold.package AS p ON p.step_reference = f.step_reference
  WHERE f.notice_date >= :period_from AND p.public_from <= :as_of
),
as_advertised AS (
  SELECT k.step_reference, r.section, r.method, r.market_approach, r.review_type, r.prequalification,
    r.estimated_amount_usd
  FROM packages AS k
  JOIN strata.silver.plan_rows AS r ON r.activity_reference_no = k.step_reference
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= k.notice_date AND v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY k.step_reference
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
)
SELECT
  k.step_reference,
  k.notice_date AS feature_date,
  coalesce(a.method, k.procurement_method) AS method,
  a.section,
  k.procurement_category AS notice_category,
  a.market_approach,
  a.review_type,
  a.prequalification,
  a.estimated_amount_usd,
  coalesce(j.country_code, k.country_code) AS country_code,
  c.region,
  k.public_from
FROM packages AS k
LEFT JOIN as_advertised AS a ON a.step_reference = k.step_reference
LEFT JOIN strata.gold.project AS j ON j.project_id = k.project_id
LEFT JOIN strata.gold.country AS c ON c.country_code = coalesce(j.country_code, k.country_code)
ORDER BY k.notice_date, k.step_reference
