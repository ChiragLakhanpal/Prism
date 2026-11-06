-- A passage of the knowledge model (ADR 0004), with its vector: the source table of the AI Search
-- index, which a Delta Sync index keeps in step with it. One row per passage of silver.passages that has
-- a vector, with what a citation's source line shows and what search filters on. The passage reader
-- (src/strata/lakehouse/passages.py) syncs it after embedding, with gold/passage.sql.
--
-- passage_id           the document, its version and the paragraph: 31525018/v1/54 (silver.passages)
-- document_id          the documents API's id, or a notice's id
-- project_id           the project, such as P130164
-- project_name         the project's name in strata.gold.project
-- country_code         the project's ISO 3166 two-letter code, which search filters on
-- country_name         the country's name, as the header writes it
-- sector               the project's one sector in Prism's taxonomy (config/sectors.toml), which search filters on
-- document_type        the documents API's type, word for word, or a notice's type
-- document_date        the document's date (docdt), or a notice's date
-- report_number        the report number, such as ICRR0021929; empty when it has none
-- version              the document's version of its report
-- section_path, paragraph, paragraph_numbered, part, parts, pdf_page, last_pdf_page, printed_page,
-- language, parse_route, kind, scanned, table_title, table_row, cells, header, text, tokens
--                      as in silver.passages
-- pdf_pages            how many pages the document's PDF has; empty for a notice
-- pdf_url              where the document's PDF is; empty for a notice
-- doc_key              the document's key in its project (silver.documents); empty for a notice
-- embedding            the vector of the header, a line break and the text (silver.passage_embeddings)
-- embedding_model      the model that made it
-- shield               the shield that scanned the passage at ingestion (silver.passage_shields)
-- attack_detected      whether it found a prompt attack; search leaves such a passage out and says why
-- replaced_on          the day a later version of the same report became public; empty while current
-- public_day           public_from as a number, 20191102, for the AI Search index's filters
-- replaced_day         replaced_on as a number, or 99991231 while the passage is current
-- public_from          the document's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.passage (
  passage_id STRING NOT NULL,
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  project_name STRING,
  country_code STRING,
  country_name STRING,
  sector STRING,
  document_type STRING NOT NULL,
  document_date DATE,
  report_number STRING,
  version INT NOT NULL,
  section_path STRING NOT NULL,
  paragraph STRING NOT NULL,
  paragraph_numbered BOOLEAN NOT NULL,
  part INT NOT NULL,
  parts INT NOT NULL,
  pdf_page INT,
  last_pdf_page INT,
  pdf_pages INT,
  printed_page STRING,
  language STRING NOT NULL,
  parse_route STRING NOT NULL,
  kind STRING NOT NULL,
  scanned BOOLEAN NOT NULL,
  table_title STRING,
  table_row INT,
  cells STRING,
  header STRING NOT NULL,
  text STRING NOT NULL,
  tokens INT NOT NULL,
  pdf_url STRING,
  doc_key STRING,
  embedding ARRAY<FLOAT> NOT NULL,
  embedding_model STRING NOT NULL,
  shield STRING,
  attack_detected BOOLEAN,
  replaced_on DATE,
  public_day INT NOT NULL,
  replaced_day INT NOT NULL,
  public_from DATE NOT NULL
)
