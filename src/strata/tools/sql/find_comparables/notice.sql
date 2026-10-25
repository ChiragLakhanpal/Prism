-- find_comparables: one notice's fields, as the evidence drawer's notice card shows a comparable's specific
-- procurement notice or its contract award notice, if it was public on the as-of date (ADR 0002). Contact
-- details never reach gold, since ingestion strips them.
SELECT
  n.notice_id,
  n.notice_type,
  n.notice_date,
  n.bid_reference_no,
  n.bid_description,
  n.procurement_category,
  n.procurement_method,
  n.market_approach,
  n.submission_deadline,
  n.contract_signature_date,
  n.signed_contract_price,
  n.signed_contract_currency,
  n.public_from
FROM strata.gold.notice AS n
WHERE n.notice_id = :notice_id
  AND n.public_from <= :as_of
