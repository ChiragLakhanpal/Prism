-- strata.gold.project: each project from the newest page the projects API returned for it.
-- key: project_id
SELECT
  project_id,
  project_name,
  country_code,
  region,
  status,
  approval_date,
  approval_fiscal_year,
  closing_date,
  implementing_agency,
  borrower,
  sector_codes,
  major_sector,
  major_sector_code,
  sector,
  sector_name,
  total_commitment_usd,
  public_from
FROM strata.silver.projects
QUALIFY row_number() OVER (PARTITION BY project_id ORDER BY fetched_at DESC, page_hash) = 1
