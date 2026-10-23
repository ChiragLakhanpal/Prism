-- One row for each page an API returned (docs/PLAN.md section 4), kept as received except for
-- the contact details that the fetch removes first (CLAUDE.md rule 8).
-- A page whose content bronze already holds is not added again.
--
-- source                   the source registry's key (config/sources.toml)
-- country_code             the two-letter code of the country the request asked for, whose
--                          watermark the page counts toward; empty for a recorded page
-- request                  the URL asked for; in the gate, the recorded file's source URL
-- page_hash                sha256 of the page, leaving out the source's ignore_keys
-- body                     the page as JSON text
-- records                  how many records the page holds
-- reported_total           how many records the source said the whole request has
-- newest_record_on         the newest date in the page's watermark field
-- contact_details_removed  the contact details removed before the page was kept: each filled contact
--                          name, address, email, phone number and web address field, and each
--                          name, email and phone number found in a notice's text
-- fetched_at               when the page was fetched, in UTC
-- public_from              the day it was fetched (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.api_pages (
  source STRING NOT NULL,
  country_code STRING,
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
