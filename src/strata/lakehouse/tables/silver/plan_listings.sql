-- Which activities each plan version lists, found in its published text (Route A), and each
-- activity's first listing: the earliest version read that lists it, which holds its first
-- published planned dates. The plan reader (src/strata/lakehouse/plans.py, read_versions) decides
-- the first listing; plan_step_delays.sql reads it from here.
--
-- document_id              the plan version
-- project_id               its project
-- activity_reference_no    STEP's Activity Reference No., such as KE-NWWDA-229129-CW-RFB
-- is_first_listing         whether this version is the activity's first listing
-- first_listing_confirmed  whether the activity's first listing is the first published one: true
--                          when every plan the documents API lists that is dated on or before it, or
--                          that has no date, was read; false when such a version went unread and may
--                          list it first
-- public_from              the version's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_listings (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  is_first_listing BOOLEAN NOT NULL,
  first_listing_confirmed BOOLEAN NOT NULL,
  public_from DATE NOT NULL
)
