-- The time estimate's features (ticket 25): every package Strata knew of on :as_of, each as it stood
-- on its feature date. A package's feature date is the day it was advertised, its specific
-- procurement notice, or :as_of for a package that was planned but not yet advertised by then: the
-- moment a package was planned or advertised, and never after :as_of (ADR 0002).
--
-- Nothing here comes from a contract, a signed amount, a Process Status, an Actual Amount or a plan
-- version published after the feature date (docs/PLAN.md section 7, the leakage traps). The Method,
-- the plan table (its category), Market Approach, Review Type, Prequalification and Estimated
-- Amount (US$) come from the newest plan version public on the feature date that lists the package,
-- in find_comparables' order (package.sql). A package no plan lists by then takes its method,
-- category and market approach from its specific procurement notice. The planned dates come from the
-- package's first listing (silver.plan_step_delays), once that listing was public. public_from is the
-- latest public date of any row read, which the replay harness checks against :as_of.
WITH notices AS (
  SELECT
    p.step_reference,
    n.notice_id,
    n.notice_date,
    n.procurement_category,
    n.procurement_method,
    n.market_approach,
    n.country_code,
    n.project_id,
    n.public_from
  FROM strata.gold.package AS p
  JOIN strata.gold.notice AS n ON n.notice_id = p.first_notice_id
  WHERE n.public_from <= :as_of
),
listings AS (
  SELECT
    r.activity_reference_no AS step_reference,
    r.document_id,
    r.project_id,
    r.section,
    r.method,
    r.market_approach,
    r.review_type,
    r.prequalification,
    r.estimated_amount_usd,
    r.pdf_page,
    v.plan_date,
    v.public_from
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= :as_of
),
known AS (
  SELECT step_reference FROM notices
  UNION
  SELECT step_reference FROM listings
),
dated AS (
  SELECT
    k.step_reference,
    n.notice_id,
    n.notice_date,
    n.procurement_category,
    n.procurement_method,
    n.market_approach,
    n.country_code,
    n.project_id,
    n.public_from,
    least(coalesce(n.notice_date, CAST(:as_of AS DATE)), CAST(:as_of AS DATE)) AS feature_date
  FROM known AS k
  LEFT JOIN notices AS n ON n.step_reference = k.step_reference
),
planned AS (
  SELECT
    d.step_reference,
    l.document_id,
    l.project_id,
    l.section,
    l.method,
    l.market_approach,
    l.review_type,
    l.prequalification,
    l.estimated_amount_usd,
    l.public_from
  FROM dated AS d
  JOIN listings AS l ON l.step_reference = d.step_reference AND l.public_from <= d.feature_date
  QUALIFY row_number() OVER (PARTITION BY d.step_reference
                             ORDER BY l.plan_date DESC, l.public_from DESC, l.document_id DESC, l.pdf_page) = 1
),
first_planned AS (
  SELECT
    d.step_reference,
    max(CASE WHEN s.step = 'Specific Procurement Notice / Invitation' THEN s.first_planned_on END) AS planned_notice_on,
    max(CASE WHEN s.step = 'Signed Contract' THEN s.first_planned_on END) AS planned_signing_on,
    max(s.public_from) AS public_from
  FROM dated AS d
  JOIN strata.silver.plan_step_delays AS s
    ON s.activity_reference_no = d.step_reference
    AND s.document_id = s.first_planned_document
    AND s.public_from <= d.feature_date
  GROUP BY d.step_reference
),
projects AS (
  SELECT
    d.step_reference,
    j.country_code,
    j.public_from
  FROM dated AS d
  LEFT JOIN planned AS pl ON pl.step_reference = d.step_reference
  JOIN strata.gold.project AS j
    ON j.project_id = coalesce(d.project_id, pl.project_id) AND j.public_from <= d.feature_date
)
SELECT
  d.step_reference,
  d.feature_date,
  d.notice_id,
  d.notice_date,
  pl.document_id AS plan_document_id,
  coalesce(pl.method, d.procurement_method) AS method,
  pl.section,
  d.procurement_category AS notice_category,
  coalesce(pl.market_approach, d.market_approach) AS market_approach,
  pl.review_type,
  pl.prequalification,
  pl.estimated_amount_usd,
  f.planned_notice_on,
  f.planned_signing_on,
  coalesce(d.country_code, j.country_code) AS country_code,
  c.region,
  greatest(d.public_from, pl.public_from, f.public_from, j.public_from, c.public_from) AS public_from
FROM dated AS d
LEFT JOIN planned AS pl ON pl.step_reference = d.step_reference
LEFT JOIN first_planned AS f ON f.step_reference = d.step_reference
LEFT JOIN projects AS j ON j.step_reference = d.step_reference
LEFT JOIN strata.gold.country AS c
  ON c.country_code = coalesce(d.country_code, j.country_code) AND c.public_from <= d.feature_date
ORDER BY d.step_reference
