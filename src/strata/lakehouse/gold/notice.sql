-- strata.gold.notice: each notice from the newest page that held it. A notice that writes its
-- credit with no lender (60300, or 6030 KE, which clean.py reads as 60300) gets the loan of its
-- own project with that number (IDA60300). Four bare digits (6030) are the older form of the
-- number, so they also match the loan whose number adds a 0. Bare digits name a loan or credit,
-- never a grant or trust fund, whose number keeps its letter and hyphen (IDA-H8060; ticket 120), so
-- only a number that is letters and then digits matches.
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
    AND regexp_extract(l.loan_number, '^[A-Z]*([0-9]+)$', 1) IN (n.loan_digits, n.loan_digits || '0')
  QUALIFY row_number() OVER (PARTITION BY n.notice_id ORDER BY l.loan_number) = 1
),
-- A notice names its country, not its code, and three names carry two codes in strata.gold.country
-- (Caribbean: 6R and CB; Serbia: RS and YF; World: 1W and 99), which gave such a notice two rows on
-- October 24, 2026. The notice's own project gives the code first; the name gives one code at most.
by_name AS (
  SELECT country_name, min(country_code) AS country_code
  FROM strata.gold.country
  GROUP BY country_name
)
SELECT
  n.notice_id,
  n.notice_type,
  n.notice_date,
  n.notice_status,
  n.project_id,
  coalesce(p.country_code, c.country_code) AS country_code,
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
LEFT JOIN strata.gold.project AS p ON p.project_id = n.project_id
LEFT JOIN by_name AS c ON c.country_name = n.project_country
