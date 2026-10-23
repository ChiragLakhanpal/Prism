-- Each project's loans and credits, from its loan transactions in the projects API.
--
-- loan_number             normalized once: the lender's letters and the number, such as IDA60300
-- loan_number_as_written  as the projects API writes it, such as IDA-60300
-- public_from             the project's public_from (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.project_loans (
  project_id STRING NOT NULL,
  loan_number STRING NOT NULL,
  loan_number_as_written STRING,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
