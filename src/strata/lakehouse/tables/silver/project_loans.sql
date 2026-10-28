-- Each project's financing numbers, from its loan transactions in the projects API: its loans and
-- credits, and its IDA grants, trust funds and the other numbers its record names (ticket 120).
--
-- loan_number             normalized once (strata.lakehouse.clean.financing_number): a loan or credit
--                         as its lender's letters and the number, such as IDA60300 or IBRD8956; any
--                         other number as its financier, one hyphen and the rest, such as IDA-H8060
-- loan_number_as_written  as the projects API writes it, such as IDA-60300
-- public_from             the project's public_from (ADR 0002)
-- financier               the letters the record writes before the number: IBRD, IDA, TF, COFN or
--                         another the records name, or null when it writes none
--
-- A table made before ticket 120 has no financier column, and CREATE TABLE IF NOT EXISTS adds none. On such
-- a workspace, run this once before the bundle deploy; it puts the column last, as here:
--   ALTER TABLE strata.silver.project_loans ADD COLUMNS (financier STRING)
CREATE TABLE IF NOT EXISTS strata.silver.project_loans (
  project_id STRING NOT NULL,
  loan_number STRING NOT NULL,
  loan_number_as_written STRING,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL,
  financier STRING
)
