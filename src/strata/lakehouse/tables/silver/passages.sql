-- One row per passage: a numbered paragraph, or a part of one, read from a document's published text
-- (Route A, src/strata/reader/passages.py). A passage is the unit every citation points to
-- (GLOSSARY.md). Rebuilt from bronze for each project on every run.
--
-- passage_id          the document, its version and the paragraph: 31525018/v1/54. A paragraph in an
--                     annex adds the annex (annex2.3), a part adds its number (54/2), and a paragraph
--                     Strata numbered starts with s (s4)
-- document_id         the documents API's id
-- project_id          the project
-- document_type       the documents API's type, word for word
-- version             the document's version of its report (silver.documents)
-- section_path        the headings above it, by their ids: III.B, Annex 2.A, an ICR Review's section
--                     number (10), or an ISR's heading
-- paragraph           the paragraph's number as the report prints it (54, or 10.b in an ICR Review), or,
--                     for a paragraph the report does not number, s and Strata's count of them (s4)
-- paragraph_numbered  whether the report itself prints that number
-- part, parts         which part of its paragraph this is, and how many parts the paragraph has: a
--                     paragraph over the token limit is divided at sentence ends
-- pdf_page            the PDF page the passage starts on, from 1
-- last_pdf_page       the PDF page it ends on
-- printed_page        the page number printed on its first page, such as "19 of 62"
-- language            the language of its text, as an ISO 639-1 code
-- parse_route         A, the published text
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
  pdf_page INT NOT NULL,
  last_pdf_page INT NOT NULL,
  printed_page STRING,
  language STRING NOT NULL,
  parse_route STRING NOT NULL,
  header STRING NOT NULL,
  text STRING NOT NULL,
  tokens INT NOT NULL,
  text_hash STRING NOT NULL,
  public_from DATE NOT NULL
)
