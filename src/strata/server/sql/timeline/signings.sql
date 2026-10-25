-- A project's timeline (ticket 23): each package of the project with a signed contract on record by the as-of
-- date (ADR 0002), on its earliest signing. A package is signed on its earliest contract in an awards dataset,
-- or, when neither dataset has one, on the Contract Signature Date of its Contract Award notice, as
-- strata.gold.package dates it. Each comes with the day its record became public, so a page as of an earlier
-- date leaves it out.
WITH awarded AS (
  SELECT
    c.step_reference,
    min(c.contract_signing_date) AS signed_on,
    :awards AS signed_in,
    CAST(NULL AS STRING) AS award_notice_id,
    sum(c.contract_amount_usd) AS signed_amount_usd,
    count(*) AS contracts,
    min(c.procurement_method) AS procurement_method,
    min(c.procurement_category) AS procurement_category,
    min(c.public_from) AS public_from
  FROM strata.gold.contract AS c
  WHERE c.project_id = :project_id
    AND c.step_reference IS NOT NULL
    AND c.source <> :notices
    AND c.contract_signing_date IS NOT NULL
    AND c.public_from <= :as_of
  GROUP BY c.step_reference
),
noticed AS (
  SELECT
    n.step_reference,
    n.contract_signature_date AS signed_on,
    :award_notice AS signed_in,
    n.notice_id AS award_notice_id,
    CASE WHEN n.signed_contract_currency = :usd THEN n.signed_contract_price END AS signed_amount_usd,
    1 AS contracts,
    n.procurement_method,
    n.procurement_category,
    n.public_from
  FROM strata.gold.notice AS n
  WHERE n.project_id = :project_id
    AND n.step_reference IS NOT NULL
    AND n.notice_type = :contract_award
    AND n.contract_signature_date IS NOT NULL
    AND n.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY n.step_reference ORDER BY n.contract_signature_date, n.notice_id) = 1
)
SELECT * FROM awarded
UNION ALL
SELECT * FROM noticed
WHERE step_reference NOT IN (SELECT step_reference FROM awarded)
ORDER BY signed_on, step_reference
