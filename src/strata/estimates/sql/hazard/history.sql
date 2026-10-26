-- The hazard model (ticket 44): every project's loan history as public by :as_of, from strata.gold.project_closing_date:
-- its first month, then each month its closing date changed. The model's rows and its outcome, a later closing-date
-- extension, are read from it, as the fixed signals' closing date check and track record read it (ticket 37).
SELECT h.project_id, h.closing_date, h.previous_closing_date, h.reported_on, h.public_from
FROM strata.gold.project_closing_date AS h
WHERE h.public_from <= :as_of
ORDER BY h.project_id, h.reported_on
