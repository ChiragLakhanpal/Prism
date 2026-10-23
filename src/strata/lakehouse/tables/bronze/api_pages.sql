-- One row for each page an API returned (docs/PLAN.md section 4), kept as received except for
-- the contact names, emails and phone numbers that the fetch removes first (CLAUDE.md rule 8).
-- A page whose content bronze already holds is not added again.
--
-- source                   the source registry's key (config/sources.toml)
-- request                  the URL asked for; in the gate, the recorded file's source URL
-- page_hash                sha256 of the page, leaving out the source's ignore_keys
-- body                     the page as JSON text
-- records                  how many records the page holds
-- reported_total           how many records the source said the whole request has
-- newest_record_on         the newest date in the page's watermark field
-- contact_details_removed  contact names, emails and phone numbers removed before the page was kept
-- fetched_at               when the page was fetched, in UTC
-- public_from              the day it was fetched (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.api_pages (
  source STRING NOT NULL,
  request STRING NOT NULL,
  page_hash STRING NOT NULL,
  body STRING NOT NULL,
  records BIGINT NOT NULL,
  reported_total BIGINT,
  newest_record_on DATE,
  contact_details_removed BIGINT NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
