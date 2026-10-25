-- rejected_bids: every Contract Award notice of the packages the call names (:refs, STEP references joined by
-- commas), published on or before the as-of date (ADR 0002), with its text after ingestion removed contact
-- details (strata.silver.notices.notice_text, the only notice text a screen may show) and its language. Newest
-- first, then by STEP reference, so a group's rows come in the order the screen lists them.
WITH texts AS (
  SELECT notice_id, notice_text, notice_language
  FROM strata.silver.notices
  WHERE notice_type = 'Contract Award'
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
)
SELECT
  g.notice_id,
  g.step_reference,
  g.notice_date,
  g.public_from,
  g.project_id,
  c.country_name,
  t.notice_text,
  t.notice_language
FROM strata.gold.notice AS g
JOIN texts AS t ON t.notice_id = g.notice_id
LEFT JOIN strata.gold.country AS c ON c.country_code = g.country_code
WHERE g.notice_type = 'Contract Award'
  AND array_contains(split(:refs, ','), g.step_reference)
  AND g.public_from <= :as_of
ORDER BY g.notice_date DESC, g.step_reference, g.notice_id
