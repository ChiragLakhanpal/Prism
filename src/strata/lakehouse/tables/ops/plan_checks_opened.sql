-- One row each time a viewer opened a plan check (ticket 15): Check a plan answered for one implementing
-- agency's Procurement Plan version. The Packages tab lists the plans a person checked beside the packages
-- they are planning, by when they last opened each. The server writes it as the app's own service
-- principal; a preview of another view writes nothing.
--
-- viewer_id            the user id the Databricks App forwarded
-- project_id           the plan's project
-- agency_id            the implementing agency's id in the plan check's address
-- implementing_agency  the agency's name as the plan writes it
-- plan_date            the plan version's date
-- latest               whether the check was of the agency's latest version, so the Packages tab links to
--                      the address that was opened
-- activities           how many activities the check covered
-- opened_at            when the viewer opened it, in UTC
-- public_from          the day they opened it, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.plan_checks_opened (
  viewer_id STRING NOT NULL,
  project_id STRING NOT NULL,
  agency_id STRING NOT NULL,
  implementing_agency STRING,
  plan_date DATE NOT NULL,
  latest BOOLEAN NOT NULL,
  activities INT,
  opened_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
