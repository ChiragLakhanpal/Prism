-- The projects that closed most recently by a date, with how many of their contracts Strata holds and how many it
-- traced from notice to signature: a contract with its award notice and its signing date (ticket 41's public Home).
-- Home keeps the first home.lines_in_view of them.
WITH closed AS (
  SELECT p.project_id, p.project_name, p.country_code, p.closing_date
  FROM strata.gold.project AS p
  WHERE p.public_from <= :as_of
    AND p.status = 'Closed'
    AND p.closing_date <= :as_of
),
counted AS (
  SELECT
    c.project_id,
    count(*) AS contracts,
    count(CASE WHEN c.award_notice_id IS NOT NULL AND c.contract_signing_date IS NOT NULL THEN 1 END) AS traced
  FROM strata.gold.contract AS c
  WHERE c.public_from <= :as_of
  GROUP BY c.project_id
)
SELECT
  closed.project_id,
  closed.project_name,
  closed.country_code,
  country.country_name,
  closed.closing_date,
  coalesce(counted.contracts, 0) AS contracts,
  coalesce(counted.traced, 0) AS traced
FROM closed
LEFT JOIN counted ON counted.project_id = closed.project_id
LEFT JOIN strata.gold.country AS country ON country.country_code = closed.country_code
ORDER BY closed.closing_date DESC, closed.project_id
