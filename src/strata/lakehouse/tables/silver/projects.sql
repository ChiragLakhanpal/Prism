-- Projects, typed and cleaned: one row per project from each fetched page. Gold reads the newest.
--
-- country_code           the ISO 3166 two-letter code the projects API gives
-- approval_fiscal_year   July to June, worked out from approval_date
-- implementing_agency    the agencies as the projects API lists them
-- major_sector_code      the major sector with the largest share of the project, in either of the
--                        projects API's two taxonomies (WX or WWX)
-- sector, sector_name    that code's sector in Prism's one taxonomy (config/sectors.toml); empty when
--                        the project lists no major sector or its code is not mapped
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
  major_sector_code STRING,
  sector STRING,
  sector_name STRING,
  total_commitment_usd DECIMAL(18, 2),
  public_disclosure_date DATE,
  last_updated_on DATE,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
