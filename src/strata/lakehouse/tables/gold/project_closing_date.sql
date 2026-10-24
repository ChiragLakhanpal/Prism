-- How a project's closing date moved, from the monthly loan history of the slice's countries: one
-- row for the first month of its history, then one for each month the closing date changed. A
-- closing-date extension is a row whose previous_closing_date is earlier than its closing_date.
--
-- closing_date            the latest closing date any of the project's loans reported that month
-- previous_closing_date   the closing date the month before; empty for the first month of its history
-- reported_on             the month end that first reported it
-- public_from             reported_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.project_closing_date (
  project_id STRING NOT NULL,
  closing_date DATE NOT NULL,
  previous_closing_date DATE,
  reported_on DATE NOT NULL,
  public_from DATE NOT NULL
)
