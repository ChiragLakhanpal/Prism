-- rebidding_risk: one activity's row in one Procurement Plan version, public on or before the as-of date (ADR
-- 0002), in STEP's columns and values word for word, for the evidence drawer's view of a canceled plan row. The
-- drawer shows the page's words: the reference and description as the plan reader read them, before the repair
-- joined a split word or swapped a look-alike character (ticket 131); a row written before the repair has none.
-- A reference the plan's text settled (reference_repair plan_text, ticket 78) is the one the page prints, so the
-- drawer leaves the parser's misreading out.
SELECT r.document_id, r.activity_reference_no, r.activity_reference_no_as_read, r.reference_repair,
  COALESCE(r.description_as_read, r.description) AS description, r.review_type, r.method, r.market_approach,
  r.estimated_amount_usd, r.process_status, r.pdf_page, v.project_id, v.implementing_agency, v.plan_date,
  v.public_from
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE r.document_id = :document_id
  AND r.activity_reference_no = :step_reference
  AND v.public_from <= :as_of
ORDER BY r.pdf_page
LIMIT 1
