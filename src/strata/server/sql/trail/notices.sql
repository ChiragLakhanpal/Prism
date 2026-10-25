-- The contract trail's notices (ticket 22): every procurement notice that carries the STEP reference, of every
-- type, in date order, with whether it was public on the as-of date (ADR 0002), so the trail can say a notice
-- became public after the page's date without showing it.
SELECT
  notice_id,
  notice_type,
  notice_date,
  notice_status,
  project_id,
  step_reference,
  bid_reference_no,
  bid_description,
  procurement_category,
  procurement_method,
  procurement_method_as_written,
  market_approach,
  submission_deadline,
  contract_signature_date,
  signed_contract_price,
  signed_contract_currency,
  public_from,
  public_from <= :as_of AS public_then
FROM strata.gold.notice
WHERE step_reference = :reference
ORDER BY notice_date, notice_id
