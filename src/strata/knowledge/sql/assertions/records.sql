-- The records of the run's projects that state a package's signing date or signed amount: the awards datasets'
-- contracts (strata.gold.contract), Contract Award notices that give a Contract Signature Date
-- (strata.gold.notice), and the Signed Contract step and Actual Amount of every plan version read
-- (strata.silver.plan_rows and plan_steps), each with the day the next version of the same agency's plan
-- replaced it and the PDF page of its row. A package with more than one contract in the awards datasets or
-- more than one such notice is left out: Prism cannot tell which notice is which lot, nor what a plan's one
-- row covers. A contract the awards datasets do not cover, which gold.contract takes from its award notice,
-- comes in once, as its notice.
-- :every_project true reads every project at once (the nightly run, ticket 43); false reads the projects in
-- :projects, joined by commas, which no project id contains (one project's page).
WITH contracts AS (
  SELECT c.step_reference, count(*) AS contracts
  FROM strata.gold.contract AS c
  WHERE array_contains(split(:contract_sources, ','), c.source) AND c.step_reference IS NOT NULL
  GROUP BY c.step_reference
),
notices AS (
  SELECT n.step_reference, count(*) AS notices
  FROM strata.gold.notice AS n
  WHERE n.notice_type = :award_notice AND n.contract_signature_date IS NOT NULL AND n.step_reference IS NOT NULL
  GROUP BY n.step_reference
),
several AS (
  SELECT step_reference FROM contracts WHERE contracts > 1
  UNION
  SELECT step_reference FROM notices WHERE notices > 1
),
versions AS (
  SELECT
    v.document_id,
    v.plan_date,
    lead(v.public_from) OVER (PARTITION BY v.project_id, v.implementing_agency
                              ORDER BY v.plan_date, v.document_id) AS replaced_on
  FROM strata.silver.plan_versions AS v
  WHERE (:every_project OR array_contains(split(:projects, ','), v.project_id))
)
SELECT
  :contract_record AS form,
  c.source AS source_key,
  c.project_id,
  c.step_reference,
  c.contract_id AS document_id,
  CAST(NULL AS STRING) AS document_type,
  c.contract_signing_date AS signed_on,
  c.contract_amount_usd AS amount_usd,
  c.public_from AS made_at,
  CAST(NULL AS DATE) AS replaced_on,
  CAST(NULL AS INT) AS pdf_page,
  c.public_from
FROM strata.gold.contract AS c
WHERE (:every_project OR array_contains(split(:projects, ','), c.project_id))
  AND array_contains(split(:contract_sources, ','), c.source)
  AND c.step_reference IS NOT NULL
  AND c.contract_signing_date IS NOT NULL
  AND c.step_reference NOT IN (SELECT step_reference FROM several)
UNION ALL
SELECT
  :award_notice_form AS form,
  :notices_source AS source_key,
  n.project_id,
  n.step_reference,
  n.notice_id AS document_id,
  n.notice_type AS document_type,
  n.contract_signature_date AS signed_on,
  CAST(NULL AS DECIMAL(18, 2)) AS amount_usd,
  n.notice_date AS made_at,
  CAST(NULL AS DATE) AS replaced_on,
  CAST(NULL AS INT) AS pdf_page,
  n.public_from
FROM strata.gold.notice AS n
WHERE (:every_project OR array_contains(split(:projects, ','), n.project_id))
  AND n.notice_type = :award_notice
  AND n.contract_signature_date IS NOT NULL
  AND n.step_reference IS NOT NULL
  AND n.step_reference NOT IN (SELECT step_reference FROM several)
UNION ALL
SELECT
  :plan_row AS form,
  :documents_source AS source_key,
  r.project_id,
  r.activity_reference_no AS step_reference,
  r.document_id,
  :plan_type AS document_type,
  s.actual_on AS signed_on,
  r.actual_amount_usd AS amount_usd,
  v.plan_date AS made_at,
  v.replaced_on,
  r.pdf_page,
  r.public_from
FROM strata.silver.plan_rows AS r
JOIN versions AS v ON v.document_id = r.document_id
JOIN strata.silver.plan_steps AS s
  ON s.document_id = r.document_id AND s.activity_reference_no = r.activity_reference_no AND s.step = :signed_step
WHERE (:every_project OR array_contains(split(:projects, ','), r.project_id))
  AND s.actual_on IS NOT NULL
  AND r.activity_reference_no NOT IN (SELECT step_reference FROM several)
ORDER BY 3, 4, 1, 5
