-- One procurement notice by its id, as the evidence drawer shows it from the contract trail (ticket 22), where it
-- was public on the as-of date (ADR 0002). Contact details were removed before the page was kept.
SELECT
  notice_id,
  notice_type,
  notice_date,
  project_id,
  step_reference,
  bid_reference_no,
  bid_description,
  procurement_method_as_written,
  submission_deadline,
  contract_signature_date,
  signed_contract_price,
  signed_contract_currency,
  public_from
FROM strata.gold.notice
WHERE notice_id = :notice_id
  AND public_from <= :as_of
