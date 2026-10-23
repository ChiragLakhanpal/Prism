-- Each response of the documents API (search.worldbank.org/api/v3/wds) as it came back: the list of
-- a project's documents with each one's type, date, disclosure date and addresses. A fetch adds a
-- row only when the response changed, so a second fetch with no change adds nothing.
--
-- source        the source registry's key, documents
-- project_id    the project the list is for
-- url           the address fetched
-- content_hash  SHA-256 of the response, which decides whether it changed
-- response      the response as JSON text
-- fetched_at    when Strata fetched it, in UTC
-- public_from   the day it was fetched: the list has no date of its own (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.document_lists (
  source STRING NOT NULL,
  project_id STRING NOT NULL,
  url STRING NOT NULL,
  content_hash STRING NOT NULL,
  response STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
