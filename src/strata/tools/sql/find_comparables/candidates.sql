-- find_comparables: every package, from every project, that matches the method, category and
-- country criteria and falls in the period, with what the other criteria and the range need. Each
-- value is one that was public on the as-of date (ADR 0002).
--
-- A package is a STEP reference (strata.gold.package). Its specific procurement notice is its first
-- notice that is not a General Procurement Notice or a Contract Award; procurement cycle time starts
-- there. It was signed on its first contract in the awards dataset, which is public from its signing
-- date, or, when it has none there, on the Contract Signature Date of its Contract Award notice,
-- which is public from the day the notice was published. A package falls in the period by its
-- notice's date, or, when Strata holds no notice for it, by its signing date, so the coverage line
-- can count it as matching but not measurable.
--
-- Process Status and Market Approach come from the newest plan version public on the as-of date
-- that lists the package. Market Approach falls back to what the contract or the notice says, which
-- only an old method name such as ICB gives. Review type and the signed amount in US dollars come
-- from its contracts. A criterion left open is a null parameter.
WITH listed AS (
  SELECT r.activity_reference_no AS step_reference, r.process_status, r.market_approach
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
),
contracts AS (
  SELECT *
  FROM strata.gold.contract
  WHERE step_reference IS NOT NULL AND source <> 'notices' AND public_from <= :as_of
),
-- A package's first contract: the earliest signed, and of contracts signed the same day the lowest
-- number, so the same package always cites the same contract.
first_contract AS (
  SELECT step_reference, contract_id
  FROM contracts
  QUALIFY row_number() OVER (PARTITION BY step_reference ORDER BY contract_signing_date, contract_id) = 1
),
signed AS (
  SELECT
    c.step_reference,
    min(c.contract_signing_date) AS signed_on,
    min(f.contract_id) AS contract_id,
    min(c.review_type) AS review_type,
    min(c.market_approach) AS market_approach,
    sum(c.contract_amount_usd) AS amount_usd
  FROM contracts AS c
  JOIN first_contract AS f ON f.step_reference = c.step_reference
  GROUP BY c.step_reference
),
award_notice AS (
  SELECT step_reference, notice_id, contract_signature_date, public_from
  FROM strata.gold.notice
  WHERE notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL AND step_reference IS NOT NULL
    AND public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY step_reference ORDER BY contract_signature_date, notice_id) = 1
),
packages AS (
  SELECT
    p.step_reference,
    p.project_id,
    p.country_code,
    c.country_name,
    p.procurement_category,
    p.procurement_method,
    CASE WHEN p.first_notice_date <= :as_of THEN p.first_notice_id END AS notice_id,
    CASE WHEN p.first_notice_date <= :as_of THEN p.first_notice_date END AS notice_date,
    f.market_approach AS notice_market_approach,
    s.signed_on,
    s.contract_id,
    s.review_type,
    s.market_approach AS contract_market_approach,
    s.amount_usd,
    a.notice_id AS award_notice_id,
    a.contract_signature_date AS award_signed_on,
    a.public_from AS award_notice_on,
    l.process_status,
    l.market_approach AS plan_market_approach
  FROM strata.gold.package AS p
  LEFT JOIN strata.gold.notice AS f ON f.notice_id = p.first_notice_id
  LEFT JOIN signed AS s ON s.step_reference = p.step_reference
  LEFT JOIN award_notice AS a ON a.step_reference = p.step_reference
  LEFT JOIN listed AS l ON l.step_reference = p.step_reference
  LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
  WHERE p.public_from <= :as_of
    AND p.step_reference <> :step_reference
    AND (CAST(:country AS STRING) IS NULL OR p.country_code = :country)
    AND (CAST(:method AS STRING) IS NULL OR p.procurement_method = :method)
    AND (CAST(:category AS STRING) IS NULL OR p.procurement_category = :category)
)
SELECT *
FROM packages
WHERE coalesce(notice_date, signed_on, award_signed_on)
  BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
ORDER BY step_reference
