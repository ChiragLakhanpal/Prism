-- The contact details ingestion took out of each page bronze keeps, by kind (ticket 45; CLAUDE.md rule 8;
-- src/strata/lakehouse/contacts.py, strip_counted). bronze.store writes one row per page and kind beside the page,
-- so the Governance page counts what was removed without reading a notice. Only counts are kept, never a value.
-- A page's kinds add up to its contact_details_removed in strata.bronze.api_pages, as its any row does.
--
-- source       the source the page came from (config/sources.toml)
-- country_code the page's country, as bronze.api_pages keeps it; empty for a source fetched for every country
-- page_hash    the page, as bronze.api_pages keys it
-- kind         names, emails, phones, addresses or web_addresses; or any, every kind together, so a count of
--              notices counts a notice once whatever it lost
-- removed      how many of that kind came out of the page
-- records      how many of the page's records (notices) had that kind taken out
-- fetched_at   when the page was fetched, in UTC
-- public_from  the day it was fetched, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.contact_removals (
  source STRING NOT NULL,
  country_code STRING,
  page_hash STRING NOT NULL,
  kind STRING NOT NULL,
  removed INT NOT NULL,
  records INT NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
