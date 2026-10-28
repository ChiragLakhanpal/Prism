-- Each financing number and the project it finances: its loans and credits, so a loan number in any
-- of the forms that strata.lakehouse.clean names (IDA-60300, 60300, 6030-KE and others) joins to its
-- project once normalized, and its IDA grants, trust funds and the other numbers its record names.
--
-- loan_number            a loan or credit as the lender's letters and the number, such as IDA60300;
--                        any other number as its financier, one hyphen and the rest, such as IDA-H8060
-- loan_number_as_written as the projects API writes it, such as IDA-60300
-- public_from            the project's public_from (ADR 0002)
-- financier              IBRD, IDA, TF, COFN or another the record names (ticket 120)
--
-- A table made before ticket 120 has no financier column, and CREATE TABLE IF NOT EXISTS adds none. On such
-- a workspace, run this once before the bundle deploy; it puts the column last, as here and in the query
-- (gold/project_loan.sql), whose columns gold compares with the table's in order:
--   ALTER TABLE strata.gold.project_loan ADD COLUMNS (financier STRING)
CREATE TABLE IF NOT EXISTS strata.gold.project_loan (
  loan_number STRING NOT NULL,
  project_id STRING NOT NULL,
  loan_number_as_written STRING,
  public_from DATE NOT NULL,
  financier STRING
)
