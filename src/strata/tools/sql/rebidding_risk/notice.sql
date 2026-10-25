-- rebidding_risk: one notice by its id, any type, published on or before the as-of date (ADR 0002), with its text
-- after ingestion removed contact details (strata.silver.notices.notice_text, the only notice text a screen may
-- show), for the evidence drawer's view of a notice a package advertised again cites.
WITH texts AS (
  SELECT notice_id, notice_text
  FROM strata.silver.notices
  WHERE notice_id = :notice_id
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
)
SELECT g.notice_id, g.notice_type, g.notice_date, g.step_reference, g.project_id, g.submission_deadline,
  g.public_from, t.notice_text
FROM strata.gold.notice AS g
JOIN texts AS t ON t.notice_id = g.notice_id
WHERE g.notice_id = :notice_id
  AND g.public_from <= :as_of
