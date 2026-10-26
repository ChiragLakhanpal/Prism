-- The projects whose records were public by a date (ticket 41): as of a past date, Home counts and checks only the
-- followed projects among them, so a project not yet public then is never counted (ADR 0002).
SELECT p.project_id
FROM strata.gold.project AS p
WHERE p.public_from <= :as_of
