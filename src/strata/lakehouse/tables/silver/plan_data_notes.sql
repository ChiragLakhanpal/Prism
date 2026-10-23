-- Where a plan row's record is weak. Built by src/strata/lakehouse/sql/plans/plan_data_notes.sql.
--
-- document_id            the plan version
-- project_id             its project
-- activity_reference_no  Activity Reference No.
-- note                   method_differs_from_reference: the reference ends in one method's code
--                        and the Method column names another (Strata uses the Method column);
--                        actual_amount_zero: a Signed or Completed row's Actual Amount reads 0.00
-- reference_method_code  the method code the reference ends in, such as RFB
-- reference_method       the method that code stands for, such as Request for Bids
-- method                 the Method column
-- process_status         the Process Status column
-- actual_amount_usd      the Actual Amount (US$) column
-- public_from            the version's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_data_notes (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  note STRING NOT NULL,
  reference_method_code STRING,
  reference_method STRING,
  method STRING,
  process_status STRING,
  actual_amount_usd DECIMAL(18, 2),
  public_from DATE NOT NULL
)
