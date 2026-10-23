-- strata.gold.notice: each notice from the newest page that held it. A notice that writes its
-- credit with no lender (60300, or 6030 KE, which clean.py reads as 60300) gets the loan of its
-- own project with that number (IDA60300). Four bare digits (6030) are the older form of the
-- number, so they also match the loan whose number adds a 0.
-- key: notice_id
WITH latest AS (
  SELECT *
  FROM strata.silver.notices
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC, page_hash) = 1
),
resolved AS (
  SELECT
    n.notice_id,
    coalesce(n.loan_number, l.loan_number) AS loan_number
  FROM latest AS n
  LEFT JOIN strata.gold.project_loan AS l
    ON n.loan_number IS NULL
    AND l.project_id = n.project_id
    AND regexp_extract(l.loan_number, '([0-9]+)', 1) IN (n.loan_digits, n.loan_digits || '0')
  QUALIFY row_number() OVER (PARTITION BY n.notice_id ORDER BY l.loan_number) = 1
)
SELECT
  n.notice_id,
  n.notice_type,
  n.notice_date,
  n.notice_status,
  n.project_id,
  c.country_code,
  n.step_reference,
  n.reference_method_code,
  n.bid_reference_no,
  n.bid_description,
  n.procurement_category,
  n.procurement_method,
  n.procurement_method_code,
  n.procurement_method_as_written,
  n.market_approach,
  n.submission_deadline,
  r.loan_number,
  n.contract_signature_date,
  n.contract_fiscal_year,
  n.signed_contract_price,
  n.signed_contract_currency,
  n.public_from
FROM latest AS n
JOIN resolved AS r ON r.notice_id = n.notice_id
LEFT JOIN strata.gold.country AS c ON c.country_name = n.project_country
