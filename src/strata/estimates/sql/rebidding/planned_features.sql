-- The rebidding models' features for every activity a Procurement Plan public on the as-of date lists (ticket
-- 28), as its newest such plan version plans it (ADR 0002): what the nightly job scores, and what a backtest's
-- models are tested on, each package as planned on the cutoff. A package's country and region come from its
-- project. No Process Status, Actual Amount or signed amount is read.
WITH planned AS (
  SELECT r.activity_reference_no AS step_reference, r.project_id, r.section, r.method, r.market_approach,
    r.review_type, r.prequalification, r.estimated_amount_usd, v.public_from
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
)
SELECT
  k.step_reference,
  CAST(:as_of AS DATE) AS feature_date,
  k.method,
  k.section,
  CAST(NULL AS STRING) AS notice_category,
  k.market_approach,
  k.review_type,
  k.prequalification,
  k.estimated_amount_usd,
  j.country_code,
  c.region,
  k.public_from
FROM planned AS k
LEFT JOIN strata.gold.project AS j ON j.project_id = k.project_id
LEFT JOIN strata.gold.country AS c ON c.country_code = j.country_code
ORDER BY k.step_reference
