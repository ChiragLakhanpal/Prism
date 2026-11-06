-- The project's notices dated since :since and public by the as-of date (ADR 0002), newest first, each with its text
-- as silver keeps it (contact details stripped at ingestion, CLAUDE.md rule 8), for the procurement_notices reader
-- (ticket 147).
SELECT n.notice_id, n.notice_type, n.notice_date, n.step_reference, n.bid_reference_no, n.bid_description,
       n.procurement_method, n.procurement_category, n.submission_deadline, n.contract_signature_date,
       n.signed_contract_price, n.signed_contract_currency, n.public_from, s.notice_text
FROM strata.gold.notice AS n
LEFT JOIN (
  SELECT notice_id, max(notice_text) AS notice_text
  FROM strata.silver.notices
  WHERE project_id = :project_id
  GROUP BY notice_id
) AS s ON s.notice_id = n.notice_id
WHERE n.project_id = :project_id
  AND n.notice_date >= :since
  AND n.public_from <= :as_of
ORDER BY n.notice_date DESC, n.notice_id DESC
