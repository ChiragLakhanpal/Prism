-- The text of each page of a document's PDF (its pdfurl), read from the PDF's text layer. It gives
-- every page its PDF page number, which the published text does not always mark, and the page
-- router reads it to send each page down Route A or Route B.
--
-- document_id   the documents API's id
-- project_id    the project the document belongs to
-- pdf_page      the page's number in the PDF, from 1
-- url           the PDF's address
-- page_hash     SHA-256 of the page's text, which says whether a page already parsed has changed
-- text          the page's text
-- fetched_at    when Prism fetched the PDF, in UTC
-- public_from   as for the document's text (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.document_pages (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  pdf_page INT NOT NULL,
  url STRING NOT NULL,
  page_hash STRING NOT NULL,
  text STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
