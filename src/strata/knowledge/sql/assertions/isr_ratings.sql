-- The ISR ratings ticket 18 read from each ISR's own ratings table (strata.silver.isr_ratings), for the
-- run's projects, each with its report (strata.silver.documents) and the passages on its PDF page that hold the
-- rating's name, of which the reader keeps the first: the passage a claim cites for the rating.
-- :every_project true reads every project at once (the nightly run, ticket 43); false reads the projects in
-- :projects, joined by commas, which no project id contains (one project's page).
SELECT
  r.document_id,
  r.project_id,
  r.isr_date,
  r.sequence,
  r.rating_name,
  r.current_rating,
  r.pdf_page,
  r.public_from,
  d.document_type,
  d.report_number,
  d.version,
  d.replaced_on,
  p.passage_id,
  pr.approval_date
FROM strata.silver.isr_ratings AS r
JOIN strata.silver.documents AS d ON d.document_id = r.document_id
LEFT JOIN strata.gold.project AS pr ON pr.project_id = r.project_id
LEFT JOIN strata.silver.passages AS p
  ON p.document_id = r.document_id AND p.pdf_page = r.pdf_page AND instr(p.text, r.rating_name) > 0
WHERE (:every_project OR array_contains(split(:projects, ','), r.project_id))
ORDER BY r.rating_name, r.isr_date, r.document_id, p.passage_id
