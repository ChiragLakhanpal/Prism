-- One row per published version of a project's Procurement Plan. The versions form one series per
-- implementing agency, read from each plan's Executing Agency(ies) line. Rebuilt from bronze on
-- every run (src/strata/lakehouse/plans.py).
--
-- document_id           the documents API's id, such as 40132287
-- project_id            the project, such as P156634
-- implementing_agency   the plan's Executing Agency(ies), word for word
-- plan_date             the plan's date in the documents API (docdt)
-- disclosed_on          its disclosure date in the documents API
-- series_order          its place in the agency's series, from 1 for the earliest
-- previous_document_id  the agency's version just before it
-- is_latest             whether it is the agency's latest version
-- pdf_pages             how many pages its PDF has
-- route_b_pages         how many of them hold a STEP table and go to the layout parser when the
--                       version is chosen
-- parse_reason          why the layout parser reads its tables: the latest version, the version
--                       before the latest, or the first version to list an activity; empty when
--                       only its text is read
-- text_url, pdf_url     where its published text and its PDF are
-- public_from           its disclosure date, or the day Prism first fetched it where that is
--                       missing or later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_versions (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  implementing_agency STRING,
  plan_date DATE NOT NULL,
  disclosed_on DATE,
  series_order INT NOT NULL,
  previous_document_id STRING,
  is_latest BOOLEAN NOT NULL,
  pdf_pages INT NOT NULL,
  route_b_pages INT NOT NULL,
  parse_reason STRING,
  text_url STRING NOT NULL,
  pdf_url STRING NOT NULL,
  public_from DATE NOT NULL
)
