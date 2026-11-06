-- Every passage of the project's ISRs made public by the as-of date and not replaced by then (ADR 0002), newest
-- report first, for the isr_narrative reader (ticket 147), which keeps the newest reports' passages on implementation
-- status and the comments on achieving targets.
SELECT p.passage_id, p.document_id, p.document_date, p.report_number, p.section_path, p.paragraph, p.pdf_page,
       p.printed_page, p.text, p.pdf_url, p.public_from
FROM strata.gold.passage AS p
WHERE p.project_id = :project_id
  AND p.document_type = :document_type
  AND p.public_from <= :as_of
  AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)
ORDER BY p.document_date DESC, p.document_id DESC, p.pdf_page, p.passage_id
