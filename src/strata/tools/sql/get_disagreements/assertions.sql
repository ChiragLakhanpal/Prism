-- get_disagreements: the assertions about a subject (a project with its packages, or one package by its STEP
-- reference) whose source was public on the as-of date (ADR 0002), read as the viewer. The tool keeps the
-- ones no later version had replaced by then. An assertion that rests on a passage comes with the paragraph
-- as the report numbers it, its printed page, its document's key in the source view's address, the
-- passage's text, which a claim quotes from, and what Prompt Shields found in it, which decides whether the
-- tool hands that text to the agent (strata.knowledge.shields.held_back), and its source line's fields.
SELECT
  a.assertion_id,
  a.subject_kind,
  a.subject_id,
  a.project_id,
  a.attribute,
  a.attribute_kind,
  a.field_name,
  a.value,
  a.value_form,
  a.judgment,
  a.period_event,
  a.period_start,
  a.period_end,
  a.made_at,
  a.replaced_on,
  a.evidence_tier,
  a.form,
  a.source_key,
  a.document_id,
  a.document_type,
  a.report_number,
  a.version,
  a.sequence,
  a.passage_id,
  a.evidence_id,
  a.pdf_page,
  a.quote,
  a.read_by,
  a.public_from,
  p.paragraph,
  p.paragraph_numbered,
  p.printed_page,
  p.doc_key,
  p.text,
  p.attack_detected,
  p.section_path,
  p.language,
  p.kind,
  -- The passage's source line, as search_passages gives it (strata.tools.search_passages.passage_source).
  p.kind AS passage_kind,
  p.document_type AS passage_document_type,
  p.project_id AS passage_project_id,
  p.project_name AS passage_project_name,
  p.document_id AS passage_document_id,
  p.document_date AS passage_document_date,
  p.report_number AS passage_report_number,
  p.version AS passage_version,
  p.section_path AS passage_section_path,
  p.paragraph AS passage_paragraph,
  p.paragraph_numbered AS passage_paragraph_numbered,
  p.pdf_page AS passage_pdf_page,
  p.pdf_pages AS passage_pdf_pages,
  p.pdf_url AS passage_pdf_url,
  p.doc_key AS passage_doc_key
FROM strata.gold.assertion AS a
LEFT JOIN strata.gold.passage AS p ON a.evidence_id = concat(:passages, p.passage_id)
WHERE (a.project_id = :subject_id OR (a.subject_kind = :package AND a.subject_id = :subject_id))
  AND a.public_from <= :as_of
ORDER BY a.subject_id, a.attribute, a.period_end, a.made_at, a.assertion_id
