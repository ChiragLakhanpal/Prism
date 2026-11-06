-- A World Bank project, from the newest page the projects API returned for it.
--
-- approval_fiscal_year   July to June, worked out from approval_date
-- major_sector_code      the major sector with the largest share, in either of the API's taxonomies
-- sector, sector_name    its one sector in Prism's taxonomy (config/sectors.toml)
-- public_from            the public disclosure date, else the approval date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.project (
  project_id STRING NOT NULL,
  project_name STRING,
  country_code STRING,
  region STRING,
  status STRING,
  approval_date DATE,
  approval_fiscal_year INT,
  closing_date DATE,
  implementing_agency STRING,
  borrower STRING,
  sector_codes STRING,
  major_sector STRING,
  major_sector_code STRING,
  sector STRING,
  sector_name STRING,
  total_commitment_usd DECIMAL(18, 2),
  public_from DATE NOT NULL
)
