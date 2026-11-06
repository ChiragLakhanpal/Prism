-- One row per document version the passage reader read (src/strata/lakehouse/passages.py): a PAD, an
-- ISR, an ICR or an ICR Review, with the version it is of its report. A report in two languages is two
-- documents, each its own first version. Rebuilt from bronze for each
-- project on every run.
--
-- document_id     the documents API's id, such as 31525018
-- project_id      the project, such as P130164
-- document_type   the documents API's type (docty), word for word
-- report_number   the documents API's report number (repnb), such as ICRR0021929; empty when it has none
-- version         1 for a report's first issue, 2 for its first re-issue under the same number, by date
-- document_date   the document's date in the documents API (docdt)
-- disclosed_on    its disclosure date in the documents API
-- language        the language of its text, as an ISO 639-1 code such as en
-- title           its title in the documents API
-- pdf_pages       how many pages its PDF has
-- text_paged      whether its published text divides into the PDF's pages on form feeds, so Route A
--                 reads it; a scan's text does not, and its pages wait for Route B
-- text_url, pdf_url  where its published text and its PDF are
-- replaced_on     the day a later version of the same report became public, after which current
--                 answers use that version; empty while this is the latest
-- doc_key         the document's key in its project, as an address names it: its type's short name and
--                 its date (icr-2019-10-10, isr-2016-08-26), with -2 for the second of a type on one date
-- parse_parts     how many parts the layout parser reads it in: 1, or more for a document longer than
--                 ingestion.parser_part_pages (config/thresholds.toml)
-- public_from     its disclosure date, or the day Prism first fetched it where that is missing or
--                 later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.documents (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  document_type STRING NOT NULL,
  report_number STRING,
  version INT NOT NULL,
  document_date DATE NOT NULL,
  disclosed_on DATE,
  language STRING NOT NULL,
  title STRING,
  pdf_pages INT NOT NULL,
  text_paged BOOLEAN NOT NULL,
  text_url STRING NOT NULL,
  pdf_url STRING NOT NULL,
  replaced_on DATE,
  doc_key STRING NOT NULL,
  parse_parts INT NOT NULL,
  public_from DATE NOT NULL
)
