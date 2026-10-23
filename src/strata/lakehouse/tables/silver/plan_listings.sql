-- Which activities each plan version lists, found in its published text (Route A). The earliest
-- version that lists an activity holds its first published planned dates.
--
-- document_id            the plan version
-- project_id             its project
-- activity_reference_no  STEP's Activity Reference No., such as KE-NWWDA-229129-CW-RFB
-- public_from            the version's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_listings (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  public_from DATE NOT NULL
)
