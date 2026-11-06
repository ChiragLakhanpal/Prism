-- The plan rows of the run's projects that say a package's contract is not signed yet (ticket 132): every version's
-- row whose Process Status is a state before signing (:pending, joined by commas, which check_plan's
-- PENDING_STATUSES defines) and whose Signed Contract step has no actual date. Each comes with its plan's date, the
-- day the next version of the same agency's plan replaced it (as records.sql gives a plan row's), and the PDF page
-- of its row. A package with more than one contract in the awards datasets or more than one award notice is left
-- out, as records.sql leaves it out: Prism cannot tell which contract a plan's one row is about.
-- :every_project true reads every project at once (the nightly run, ticket 43); false reads the projects in
-- :projects, joined by commas, which no project id contains (one project's page).
WITH several AS (
  SELECT c.step_reference
  FROM strata.gold.contract AS c
  WHERE array_contains(split(:contract_sources, ','), c.source) AND c.step_reference IS NOT NULL
  GROUP BY c.step_reference
  HAVING count(*) > 1
  UNION
  SELECT n.step_reference
  FROM strata.gold.notice AS n
  WHERE n.notice_type = :award_notice AND n.contract_signature_date IS NOT NULL AND n.step_reference IS NOT NULL
  GROUP BY n.step_reference
  HAVING count(*) > 1
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
  r.project_id,
  r.activity_reference_no AS step_reference,
  r.document_id,
  r.process_status,
  v.plan_date,
  v.replaced_on,
  r.pdf_page,
  r.public_from
FROM strata.silver.plan_rows AS r
JOIN versions AS v ON v.document_id = r.document_id
LEFT JOIN strata.silver.plan_steps AS s
  ON s.document_id = r.document_id AND s.activity_reference_no = r.activity_reference_no AND s.step = :signed_step
WHERE (:every_project OR array_contains(split(:projects, ','), r.project_id))
  AND array_contains(split(:pending, ','), r.process_status)
  AND s.actual_on IS NULL
  AND r.activity_reference_no IS NOT NULL
  AND r.activity_reference_no NOT IN (SELECT step_reference FROM several)
ORDER BY 1, 2, 5, 3
