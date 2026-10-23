-- The Planned and Actual date of each STEP step of each activity, in each plan version the layout
-- parser read. A step the plan leaves blank has a row with no dates.
--
-- document_id            the plan version
-- project_id             its project
-- activity_reference_no  Activity Reference No.
-- step                   STEP's name for the step, word for word, such as Signed Contract
-- step_order             the step's place in its table, from 1
-- planned_on             the step's Planned date in this version
-- actual_on              the step's Actual date in this version
-- public_from            the version's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_steps (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  step STRING NOT NULL,
  step_order INT NOT NULL,
  planned_on DATE,
  actual_on DATE,
  public_from DATE NOT NULL
)
