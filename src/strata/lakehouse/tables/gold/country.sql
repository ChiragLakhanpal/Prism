-- A borrowing country, by its ISO 3166 two-letter code.
--
-- public_from   the earliest public_from of any project, award or notice for the country (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.country (
  country_code STRING NOT NULL,
  country_name STRING,
  region STRING,
  public_from DATE NOT NULL
)
