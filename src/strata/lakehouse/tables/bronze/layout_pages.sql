-- What the layout parser (Route B) read on each page: the page's tables, as JSON. Each page is
-- parsed once: a page whose document_id, pdf_page and page_hash already have a row is not parsed
-- again, and the rows here count against the daily page cap on the day they were parsed.
--
-- document_id   the documents API's id
-- project_id    the project the document belongs to
-- pdf_page      the page's number in the PDF, from 1
-- page_hash     SHA-256 of the page's text when it was parsed (bronze.document_pages)
-- parser        the layout parser that read it: ai_parse_document, or the offline stand-in
-- tables        the page's tables as JSON: {"tables": [{"title", "header_rows", "rows"}]}
-- parsed_at     when it was parsed, in UTC
-- run_id        the run that parsed it
-- public_from   the document's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.layout_pages (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  pdf_page INT NOT NULL,
  page_hash STRING NOT NULL,
  parser STRING NOT NULL,
  tables STRING NOT NULL,
  parsed_at TIMESTAMP NOT NULL,
  run_id STRING NOT NULL,
  public_from DATE NOT NULL
)
