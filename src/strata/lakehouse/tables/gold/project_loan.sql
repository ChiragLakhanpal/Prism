-- Each loan or credit and the project it finances, so a loan number in any of its four forms
-- (IDA60300, IDA-60300, IDA / 60300, 60300) joins to its project once normalized.
--
-- loan_number            the lender's letters and the number, such as IDA60300
-- loan_number_as_written as the projects API writes it, such as IDA-60300
-- public_from            the project's public_from (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.project_loan (
  loan_number STRING NOT NULL,
  project_id STRING NOT NULL,
  loan_number_as_written STRING,
  public_from DATE NOT NULL
)
