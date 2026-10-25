-- The baseline of each implementing agency's Procurement Plans for a project (ticket 21): the version a
-- World Bank staff member saved as the plan agreed at negotiations. Every World Bank staff viewer who
-- checks that agency's plans sees the same baseline, and later checks also measure delay from its dates.
-- One row per project and agency. The app writes it with the viewer's own token (src/strata/server/
-- baseline.py); saving another version replaces the row, and removing it deletes the row with a DELETE
-- that names the project and the agency (CLAUDE.md rule 5).
--
-- project_id            the project, such as P156634
-- agency_id             check_plan's id for the agency, such as northern-water-works-development-agency
-- implementing_agency   the agency's name, as its plan's Executing Agency(ies) line gives it
-- document_id           the saved version's id in the documents API
-- plan_date             the saved version's date
-- saved_by              the user id of the person who saved it
-- saved_by_name         their display name in the workspace, shown only in the World Bank staff view
-- saved_at              when they saved it, in UTC
-- public_from           the day they saved it: an as-of view shows the baseline only from then (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.plan_baselines (
  project_id STRING NOT NULL,
  agency_id STRING NOT NULL,
  implementing_agency STRING NOT NULL,
  document_id STRING NOT NULL,
  plan_date DATE NOT NULL,
  saved_by STRING NOT NULL,
  saved_by_name STRING,
  saved_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
