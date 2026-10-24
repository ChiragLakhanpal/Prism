-- search_passages: the passages a searcher ranked, read from strata.gold.passage as the viewer, each
-- only where it was public on the as-of date and not yet replaced by a re-issue of its report then
-- (ADR 0002). :ids holds the ranked passage ids joined by commas, which no passage id contains.
SELECT
  p.passage_id,
  p.document_id,
  p.project_id,
  p.project_name,
  p.document_type,
  p.document_date,
  p.report_number,
  p.version,
  p.section_path,
  p.paragraph,
  p.paragraph_numbered,
  p.part,
  p.parts,
  p.pdf_page,
  p.last_pdf_page,
  p.pdf_pages,
  p.printed_page,
  p.language,
  p.parse_route,
  p.kind,
  p.scanned,
  p.table_title,
  p.table_row,
  p.cells,
  p.header,
  p.text,
  p.pdf_url,
  p.doc_key,
  p.attack_detected,
  p.public_from
FROM strata.gold.passage AS p
WHERE array_contains(split(:ids, ','), p.passage_id)
  AND p.public_from <= :as_of
  AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)
