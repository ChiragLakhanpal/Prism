-- The latest ISR ratings the projects API keeps for each project, one row per rating from each
-- fetched page. The API lists some ratings twice; a page's rows hold each one once.
--
-- rating_code   the API's code for what is rated, such as 27 for Procurement
-- rating_name   what is rated, such as Procurement or Progress towards achievement of PDO
-- isr_date      the date of the ISR that gave the rating
-- value         the rating, such as Moderately Satisfactory
-- public_from   isr_date, or the fetch day when it is missing or later (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.project_isr_ratings (
  project_id STRING NOT NULL,
  rating_code STRING NOT NULL,
  rating_name STRING,
  isr_date DATE,
  value STRING,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
