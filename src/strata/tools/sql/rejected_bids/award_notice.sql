-- rejected_bids: one Contract Award notice by its id, published on or before the as-of date (ADR 0002), with its
-- text after ingestion removed contact details, for the evidence drawer's view of a rejected-bid row.
WITH texts AS (
  SELECT notice_id, notice_text
  FROM strata.silver.notices
  WHERE notice_id = :notice_id
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
)
SELECT g.notice_id, g.step_reference, g.notice_date, g.public_from, g.project_id, t.notice_text
FROM strata.gold.notice AS g
JOIN texts AS t ON t.notice_id = g.notice_id
WHERE g.notice_id = :notice_id
  AND g.notice_type = 'Contract Award'
  AND g.public_from <= :as_of
