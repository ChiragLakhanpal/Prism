-- One procurement notice by its id, as the evidence drawer shows it from the contract trail (ticket 22) or from a
-- package advertised again (ticket 28), where it was public on the as-of date (ADR 0002), with its text after
-- ingestion removed contact details (strata.silver.notices.notice_text, the only notice text a screen may show),
-- for the sentence that says why it went out again. Contact details were removed before the page was kept.
WITH texts AS (
  SELECT notice_id, notice_text
  FROM strata.silver.notices
  WHERE notice_id = :notice_id
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
)
SELECT
  g.notice_id,
  g.notice_type,
  g.notice_date,
  g.project_id,
  g.step_reference,
  g.bid_reference_no,
  g.bid_description,
  g.procurement_method_as_written,
  g.submission_deadline,
  g.contract_signature_date,
  g.signed_contract_price,
  g.signed_contract_currency,
  g.public_from,
  t.notice_text
FROM strata.gold.notice AS g
LEFT JOIN texts AS t ON t.notice_id = g.notice_id
WHERE g.notice_id = :notice_id
  AND g.public_from <= :as_of
