-- The documents each document run read (src/strata/lakehouse/passages.py), per document type and fiscal
-- year of disclosure, with the pages each route read and read well. The dashboard's Data readiness page
-- pivots it, and docs/PLAN.md section 3's page estimates are checked against it.
--
-- run_id                   the document run
-- document_type            the documents API's type, word for word
-- fiscal_year              the World Bank fiscal year of its disclosure date, July to June (FY2020 runs
--                          from July 1, 2019); the day Strata first fetched it when the date is missing
-- documents                how many documents of that type and year the run read
-- pdf_pages                their pages, in the PDFs
-- pages_route_a            the pages Route A read from the published text
-- pages_route_b            the pages the page router sent to the layout parser
-- pages_read_well_route_a  the pages of published text that have text
-- pages_read_well_route_b  the pages the layout parser read and recovered a table or text from
-- measured_at              when, in UTC
-- public_from              the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.documents_read (
  run_id STRING NOT NULL,
  document_type STRING NOT NULL,
  fiscal_year INT,
  documents BIGINT NOT NULL,
  pdf_pages BIGINT NOT NULL,
  pages_route_a BIGINT NOT NULL,
  pages_route_b BIGINT NOT NULL,
  pages_read_well_route_a BIGINT NOT NULL,
  pages_read_well_route_b BIGINT NOT NULL,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
