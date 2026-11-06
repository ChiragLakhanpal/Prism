-- Each answer a deep research source gave, kept by its address so a run within the source's cache_hours reuses it
-- rather than call the source again (ticket 147; src/strata/research/fetching.py). Only an answer of 200 is kept, so
-- a refusal is never reused as if it were the source's answer. Written as the app's own service principal; rows only
-- grow, and a read takes the newest answer for an address.
--
-- url          the address asked
-- source_key   the registry's key for the source (config/research.toml)
-- status       the HTTP status the source answered
-- headers      the answer's headers, as JSON
-- body         the answer's body, base64
-- fetched_at   when Prism fetched it, in UTC
-- public_from  the day it was fetched (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.research_cache (
  url STRING NOT NULL,
  source_key STRING NOT NULL,
  status INT NOT NULL,
  headers STRING NOT NULL,
  body STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
