-- Each step of each activity in each plan version read, with the step's first published planned
-- date and its delay. Built by src/strata/lakehouse/sql/plans/plan_step_delays.sql, the one place
-- that defines delay (GLOSSARY.md): the days from the first published planned date to the actual date.
--
-- document_id              the plan version
-- project_id               its project
-- activity_reference_no    Activity Reference No.
-- step                     STEP's name for the step
-- step_order               the step's place in its table, from 1
-- planned_on, actual_on    the step's dates in this version
-- first_planned_on         the step's Planned date in the activity's first listing (silver.plan_listings);
--                          empty until that version's tables are read, or when it plans no date for the step
-- first_planned_document   the first listing's document_id
-- first_planned_plan_date  the first listing's date
-- first_listing_confirmed  whether the first listing is the first published one; false when an older
--                          listed version went unread, so the delay may be measured from a later date
-- delay_days               actual_on minus first_planned_on, in days; empty until both are known
-- public_from              the version's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_step_delays (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  step STRING NOT NULL,
  step_order INT NOT NULL,
  planned_on DATE,
  actual_on DATE,
  first_planned_on DATE,
  first_planned_document STRING,
  first_planned_plan_date DATE,
  first_listing_confirmed BOOLEAN,
  delay_days INT,
  public_from DATE NOT NULL
)
