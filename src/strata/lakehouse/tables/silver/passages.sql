-- One row per passage: a numbered paragraph, or a part of one, read from a document's published text
-- (Route A, src/strata/reader/passages.py) or from what the layout parser read on a scanned page
-- (Route B, src/strata/lakehouse/route_b.py); one row of a table, or the table's one summary; or a
-- section of a procurement notice's text (src/strata/lakehouse/notice_passages.py). A passage is the
-- unit every citation points to (GLOSSARY.md). Rebuilt from bronze and silver.notices for each project
-- on every run.
--
-- passage_id          the document, its version and the paragraph: 31525018/v1/54. A paragraph in an
--                     annex adds the annex (annex2.3), a part adds its number (54/2), and a paragraph
--                     Strata numbered starts with s (s4). A table is table and the PDF page it starts
--                     on (18381488/v1/table65, its summary), and its rows add their number
--                     (18381488/v1/table65.2). A notice's section is the notice and the section's
--                     number (OP00118817/v1/s3)
-- document_id         the documents API's id, or a notice's id (OP00118817)
-- project_id          the project
-- document_type       the documents API's type, word for word, or a notice's type (Invitation for Bids)
-- version             the document's version of its report (silver.documents)
-- section_path        the headings above it, by their ids: III.B, Annex 2.A, an ICR Review's section
--                     number (10), or an ISR's heading
-- paragraph           the paragraph's number as the report prints it (54, or 10.b in an ICR Review), or,
--                     for a paragraph the report does not number, s and Strata's count of them (s4)
-- paragraph_numbered  whether the report itself prints that number
-- part, parts         which part of its paragraph this is, and how many parts the paragraph has: a
--                     paragraph over the token limit is divided at sentence ends
-- pdf_page            the PDF page the passage starts on, from 1, counted in the whole PDF even when a
--                     long document is read in parts; empty for a notice, which has no pages
-- last_pdf_page       the PDF page it ends on
-- printed_page        the page number printed on its first page, such as "19 of 62"
-- language            the language of its text, as an ISO 639-1 code
-- parse_route         A, the published text, or B, the layout parser
-- kind                paragraph, table_row, table_summary (Strata's summary of a table, which never
--                     backs a number) or notice_text
-- scanned             whether the layout parser read it from a scanned page
-- table_title         a table row's or summary's table: the line above it, such as WORKS or Annex 4 -
--                     Operational Risk Assessment Framework (ORAF)
-- table_row           a table row's number in its table, from 1
-- cells               a table row's cells as JSON, [[column head, value], ...], blanks left out
-- sector              its project's one sector in Strata's taxonomy (strata.gold.project.sector, from
--                     config/sectors.toml), which search filters on; empty when its project is not in
--                     strata.gold.project or has no sector
-- header              the short header prepended before embedding: ICR, P130164, India, roads, III.B, ¶54, p.23
-- text                the paragraph's words as published, each run of spaces and line breaks written as one space
-- tokens              how many tokens the text has (strata.reader.passages.tokens)
-- text_hash           SHA-256 of the header, a line break and the text: what gets embedded and scanned
-- public_from         the document's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.passages (
  passage_id STRING NOT NULL,
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  document_type STRING NOT NULL,
  version INT NOT NULL,
  section_path STRING NOT NULL,
  paragraph STRING NOT NULL,
  paragraph_numbered BOOLEAN NOT NULL,
  part INT NOT NULL,
  parts INT NOT NULL,
  pdf_page INT,
  last_pdf_page INT,
  printed_page STRING,
  language STRING NOT NULL,
  parse_route STRING NOT NULL,
  kind STRING NOT NULL,
  scanned BOOLEAN NOT NULL,
  table_title STRING,
  table_row INT,
  cells STRING,
  sector STRING,
  header STRING NOT NULL,
  text STRING NOT NULL,
  tokens INT NOT NULL,
  text_hash STRING NOT NULL,
  public_from DATE NOT NULL
)
