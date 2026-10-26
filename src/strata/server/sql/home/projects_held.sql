-- How many projects Strata holds a record for, as of a date (ticket 41's public Home).
SELECT count(*) AS projects
FROM strata.gold.project AS p
WHERE p.public_from <= :as_of
