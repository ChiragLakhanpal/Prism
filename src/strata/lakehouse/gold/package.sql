-- strata.gold.package: each STEP reference that a notice or a contract carries, from every project.
-- A package is signed on its earliest contract in an awards dataset or, when it has none there,
-- on the Contract Signature Date of its Contract Award notice. Its Process Status is the one in
-- the newest plan version that lists it, by plan date.
-- key: step_reference
WITH notices AS (
  SELECT *
  FROM strata.gold.notice
  WHERE step_reference IS NOT NULL
),
first_notice AS (
  SELECT *
  FROM notices
  WHERE notice_type NOT IN ('General Procurement Notice', 'Contract Award')
  QUALIFY row_number() OVER (PARTITION BY step_reference ORDER BY notice_date, notice_id) = 1
),
award_notice AS (
  SELECT *
  FROM notices
  WHERE notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY step_reference ORDER BY contract_signature_date, notice_id) = 1
),
noticed AS (
  SELECT
    step_reference,
    min(project_id) AS project_id,
    min(country_code) AS country_code,
    min(procurement_category) AS procurement_category,
    min(procurement_method) AS procurement_method,
    min(reference_method_code) AS reference_method_code,
    min(public_from) AS public_from
  FROM notices
  GROUP BY step_reference
),
contracts AS (
  SELECT
    step_reference,
    min(project_id) AS project_id,
    min(country_code) AS country_code,
    min(procurement_category) AS procurement_category,
    min(procurement_method) AS procurement_method,
    min(reference_method_code) AS reference_method_code,
    min(contract_signing_date) AS signed_on,
    count(*) AS contract_count,
    min(review_type) AS review_type,
    min(public_from) AS public_from
  FROM strata.gold.contract
  WHERE step_reference IS NOT NULL AND source <> 'notices'
  GROUP BY step_reference
),
planned AS (
  SELECT r.activity_reference_no AS step_reference, r.process_status, r.document_id, v.public_from
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
),
refs AS (
  SELECT step_reference FROM noticed
  UNION
  SELECT step_reference FROM contracts
)
SELECT
  r.step_reference,
  coalesce(c.project_id, n.project_id) AS project_id,
  coalesce(c.country_code, n.country_code) AS country_code,
  coalesce(f.procurement_category, c.procurement_category, n.procurement_category) AS procurement_category,
  coalesce(c.procurement_method, f.procurement_method, n.procurement_method) AS procurement_method,
  coalesce(c.reference_method_code, n.reference_method_code) AS reference_method_code,
  f.notice_id AS first_notice_id,
  f.notice_type AS first_notice_type,
  f.notice_date AS first_notice_date,
  f.submission_deadline AS bids_due,
  coalesce(c.signed_on, a.contract_signature_date) AS contract_signed_on,
  CASE
    WHEN c.signed_on IS NOT NULL THEN 'contract awards'
    WHEN a.contract_signature_date IS NOT NULL THEN 'award notice'
  END AS signed_in,
  a.notice_id AS award_notice_id,
  CAST(coalesce(c.contract_count, 0) AS INT) AS contract_count,
  c.review_type,
  p.process_status,
  p.document_id AS process_status_document_id,
  p.public_from AS process_status_public_from,
  least(n.public_from, c.public_from) AS public_from
FROM refs AS r
LEFT JOIN noticed AS n ON n.step_reference = r.step_reference
LEFT JOIN contracts AS c ON c.step_reference = r.step_reference
LEFT JOIN first_notice AS f ON f.step_reference = r.step_reference
LEFT JOIN award_notice AS a ON a.step_reference = r.step_reference
LEFT JOIN planned AS p ON p.step_reference = r.step_reference
