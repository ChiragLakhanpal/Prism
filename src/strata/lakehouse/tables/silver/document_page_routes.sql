-- The page router's choice for each page of each document the passage reader read: Route A, the
-- text the World Bank publishes, or Route B, the layout parser (docs/PLAN.md section 5). Rebuilt from
-- bronze for each project on every run (src/strata/lakehouse/passages.py).
--
-- document_id      the documents API's id
-- project_id       the project
-- pdf_page         the page's number in the PDF, from 1
-- route            A or B
-- reason           body (Route A reads it into passages), front_matter (the cover, abbreviations and
--                  contents before the body, read and left out), data_sheet (a report's data sheet,
--                  whose tables go to Route B), risk_table (a PAD's risk table, from the page that
--                  names its risk framework to the next annex, read as a table by Route B), no_text
--                  (nothing to read, such as a figure), scanned (a page of a scan, whose published
--                  text does not divide into the PDF's pages, read by Route B) or text_not_paged (the
--                  same, before the PDF's pages were held)
-- printed_page     the page number printed on the page, such as "19 of 62" or "ii"; empty when none
-- numbering_found  whether a paragraph the report numbers has text on this page
-- passages         how many passages start on this page, from either route
-- part             the part of the document the page is read in: 1, or more for a document longer than
--                  the layout parser's page limit
-- public_from      the document's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.document_page_routes (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  pdf_page INT NOT NULL,
  route STRING NOT NULL,
  reason STRING NOT NULL,
  printed_page STRING,
  numbering_found BOOLEAN NOT NULL,
  passages INT NOT NULL,
  part INT NOT NULL,
  public_from DATE NOT NULL
)
