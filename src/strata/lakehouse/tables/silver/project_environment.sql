-- Each project's Environmental Assessment Category, from the projects API's envassesmentcategorycode,
-- one row per project from each fetched page whose record gives one (ticket 21). A project's Summary
-- shows it when the record has no risk rating under the Environmental and Social Framework.
--
-- ea_category   the category, word for word, such as B
-- public_from   as silver.projects gives the record (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.project_environment (
  project_id STRING NOT NULL,
  ea_category STRING NOT NULL,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
