-- A project's latest ISR ratings, from the newest page the projects API returned for it, each once.
-- The API keeps only the latest ISR's ratings; the rating history comes from the ISRs' own text.
--
-- rating_code   the API's code for what is rated, such as 27 for Procurement
-- rating_name   what is rated, such as Procurement
-- isr_date      the date of the ISR that gave the rating
-- value         the rating, such as Moderately Satisfactory
-- public_from   isr_date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.project_isr_rating (
  project_id STRING NOT NULL,
  rating_code STRING NOT NULL,
  rating_name STRING,
  isr_date DATE,
  value STRING,
  public_from DATE NOT NULL
)
