-- Each project's Environmental Assessment Category and its overall environmental and social risk rating
-- under the Environmental and Social Framework (ESF), from the projects API's envassesmentcategorycode
-- and esrc_ovrl_risk_rate, one row per project from each fetched page whose record gives either
-- (ticket 21). A project's Summary shows the risk rating, or the category when the record has no rating.
--
-- ea_category   the category, word for word, such as B; empty when the record gives none
-- esf_risk      the risk rating, word for word, such as Substantial; empty when the record gives none
-- public_from   as silver.projects gives the record (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.project_environment (
  project_id STRING NOT NULL,
  ea_category STRING,
  esf_risk STRING,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
