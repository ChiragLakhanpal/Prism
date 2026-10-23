-- Projects, typed and cleaned: one row per project from each fetched page. Gold reads the newest.
--
-- country_code           the ISO 3166 two-letter code the projects API gives
-- approval_fiscal_year   July to June, worked out from approval_date
-- implementing_agency    the agencies as the projects API lists them
-- total_commitment_usd   the current total commitment, in US dollars
-- public_from            the public disclosure date, else the approval date, else the fetch day (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.projects (
  project_id STRING NOT NULL,
  project_name STRING,
  country_code STRING,
  country_name STRING,
  region STRING,
  status STRING,
  approval_date DATE,
  approval_fiscal_year INT,
  closing_date DATE,
  implementing_agency STRING,
  borrower STRING,
  sector_codes STRING,
  major_sector STRING,
  total_commitment_usd DECIMAL(18, 2),
  public_disclosure_date DATE,
  last_updated_on DATE,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
