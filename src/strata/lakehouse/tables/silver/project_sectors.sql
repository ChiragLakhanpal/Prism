-- Each project's sectors with their shares, from the projects API's major_sectors, one row per sector
-- from each fetched page (ticket 21). gold.project keeps one sector in Prism's taxonomy, the major
-- sector with the largest share; a project's Summary shows the shares beside it.
--
-- major_sector_code, major_sector_name   the major sector the sector sits under, word for word
-- sector_code, sector_name               the sector, word for word, such as FY17 - Rural and Inter-Urban Roads
-- share_percent                          its share of the project, in percent
-- public_from                            as silver.projects gives the record (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.project_sectors (
  project_id STRING NOT NULL,
  major_sector_code STRING,
  major_sector_name STRING,
  sector_code STRING NOT NULL,
  sector_name STRING,
  share_percent DECIMAL(5, 1),
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
