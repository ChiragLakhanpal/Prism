-- Rebidding reasons (ticket 28): every notice of the packages :refs names (STEP references joined by commas)
-- published on or before the as-of date (ADR 0002), any type, with its text after ingestion removed contact
-- details (strata.silver.notices.notice_text, the only notice text a screen may show) and its language, oldest
-- first. strata.estimates.rebidding quotes from them the sentence that gives a reason for advertising again.
WITH texts AS (
  SELECT notice_id, notice_text, notice_language
  FROM strata.silver.notices
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
)
SELECT
  g.notice_id,
  g.notice_type,
  g.notice_date,
  g.step_reference,
  g.project_id,
  g.public_from,
  t.notice_text,
  t.notice_language
FROM strata.gold.notice AS g
JOIN texts AS t ON t.notice_id = g.notice_id
WHERE g.step_reference IS NOT NULL
  AND array_contains(split(:refs, ','), g.step_reference)
  AND g.public_from <= :as_of
ORDER BY g.notice_date, g.notice_id
