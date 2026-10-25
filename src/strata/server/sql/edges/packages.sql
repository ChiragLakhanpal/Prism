-- A project's Connections tab (ticket 22): each package the project plans (its plans edges public on the as-of
-- date, ADR 0002), with what its node shows and what the tab orders it by: its description as its notice gives it
-- (STEP typed it; the plan reader can split a word inside a plan's cell), or else as the newest plan version public
-- then gives it, its Process Status in that version, its Estimated Amount, its first planned date as first
-- published, and its contracts public then (how many, the first signing date and their amount in US dollars).
WITH refs AS (
  SELECT replace(to_id, 'strata.gold.package:', '') AS step_reference, min(public_from) AS public_from
  FROM strata.gold.edge
  WHERE kind = 'plans'
    AND from_id = concat('strata.gold.project:', :project_id)
    AND public_from <= :as_of
  GROUP BY to_id
),
latest AS (
  SELECT
    r.activity_reference_no AS step_reference,
    r.description,
    r.process_status,
    r.estimated_amount_usd
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE r.project_id = :project_id
    AND v.public_from <= :as_of
  QUALIFY row_number() OVER (
    PARTITION BY r.activity_reference_no ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page
  ) = 1
),
planned AS (
  SELECT activity_reference_no AS step_reference, min(first_planned_on) AS first_planned_on
  FROM strata.silver.plan_step_delays
  WHERE project_id = :project_id
    AND public_from <= :as_of
  GROUP BY activity_reference_no
),
signed AS (
  SELECT
    step_reference,
    count(*) AS contracts,
    min(contract_signing_date) AS first_signed_on,
    sum(contract_amount_usd) AS signed_usd,
    min(contract_description) AS description
  FROM strata.gold.contract
  WHERE project_id = :project_id
    AND public_from <= :as_of
    AND step_reference IS NOT NULL
  GROUP BY step_reference
),
noticed AS (
  SELECT step_reference, min(bid_description) AS description
  FROM strata.gold.notice
  WHERE project_id = :project_id
    AND public_from <= :as_of
    AND step_reference IS NOT NULL
  GROUP BY step_reference
)
SELECT
  refs.step_reference,
  coalesce(noticed.description, latest.description, signed.description) AS description,
  latest.process_status,
  latest.estimated_amount_usd,
  planned.first_planned_on,
  coalesce(signed.contracts, 0) AS contracts,
  signed.first_signed_on,
  signed.signed_usd
FROM refs
LEFT JOIN latest ON latest.step_reference = refs.step_reference
LEFT JOIN planned ON planned.step_reference = refs.step_reference
LEFT JOIN signed ON signed.step_reference = refs.step_reference
LEFT JOIN noticed ON noticed.step_reference = refs.step_reference
ORDER BY refs.step_reference
