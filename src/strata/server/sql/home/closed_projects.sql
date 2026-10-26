-- The closed projects whose contracts Strata holds, most recently closed first, by a date, with how many of their
-- contracts it holds and how many it traced from notice to signature (ticket 41's public Home): a contract with a
-- signing date whose STEP reference a notice of the same project carries, the link the contract trail follows
-- (sql/trail/notices.sql). A closed project with no contract, such as a Development Policy Operation, has no trail
-- and is left out. Home keeps the first home.lines_in_view of them.
WITH closed AS (
  SELECT p.project_id, p.project_name, p.country_code, p.closing_date
  FROM strata.gold.project AS p
  WHERE p.public_from <= :as_of
    AND p.status = 'Closed'
    AND p.closing_date <= :as_of
),
noticed AS (
  SELECT DISTINCT n.project_id, n.step_reference
  FROM strata.gold.notice AS n
  WHERE n.public_from <= :as_of
    AND n.step_reference IS NOT NULL
),
counted AS (
  SELECT
    c.project_id,
    count(*) AS contracts,
    count(CASE WHEN c.contract_signing_date IS NOT NULL AND noticed.step_reference IS NOT NULL THEN 1 END) AS traced
  FROM strata.gold.contract AS c
  LEFT JOIN noticed ON noticed.project_id = c.project_id AND noticed.step_reference = c.step_reference
  WHERE c.public_from <= :as_of
  GROUP BY c.project_id
)
SELECT
  closed.project_id,
  closed.project_name,
  closed.country_code,
  country.country_name,
  closed.closing_date,
  counted.contracts,
  counted.traced
FROM closed
JOIN counted ON counted.project_id = closed.project_id
LEFT JOIN strata.gold.country AS country ON country.country_code = closed.country_code
ORDER BY closed.closing_date DESC, closed.project_id
