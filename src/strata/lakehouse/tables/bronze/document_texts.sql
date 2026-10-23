-- The text the World Bank publishes for a document (its txturl), as it came back. Route A reads it.
--
-- document_id   the documents API's id, such as 40132287
-- project_id    the project the document belongs to
-- url           the address fetched
-- content_hash  SHA-256 of the text
-- text          the text, byte for byte as UTF-8
-- fetched_at    when Strata fetched it, in UTC
-- public_from   the document's disclosure date, or the day it was fetched where that date is
--               missing or later than the fetch (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.document_texts (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  url STRING NOT NULL,
  content_hash STRING NOT NULL,
  text STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
