-- One STEP row per activity in each plan version the layout parser read, in STEP's columns and
-- with STEP's values word for word. The method comes from the Method column, never from the
-- reference. A column the plan's template lacks is empty.
--
-- document_id                 the plan version
-- project_id                  its project
-- section                     the table the row sits in: WORKS, GOODS, NON CONSULTING SERVICES,
--                             CONSULTING FIRMS or INDIVIDUAL CONSULTANTS
-- activity_reference_no       Activity Reference No.
-- description                 Description (a space marks each place the PDF cell wrapped)
-- loan_credit_no              Loan / Credit No.
-- component                   Component
-- review_type                 Review Type: Prior or Post
-- method                      Method, such as Request for Bids
-- market_approach             Market Approach, such as Open - National
-- procurement_process         Procurement Process, such as Single Stage - One Envelope
-- prequalification            Prequalification (Y/N)
-- high_sea_sh_risk            High SEA/SH Risk
-- procurement_document_type   Procurement Document Type
-- contract_type               Contract Type (consultants)
-- estimated_amount_usd        Estimated Amount (US$)
-- actual_amount_usd           Actual Amount (US$)
-- process_status              Process Status, such as Pending Implementation or Signed
-- pdf_page                    the PDF page the row is on
-- parser                      the layout parser that read the page
-- public_from                 the version's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.plan_rows (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  section STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  description STRING,
  loan_credit_no STRING,
  component STRING,
  review_type STRING,
  method STRING,
  market_approach STRING,
  procurement_process STRING,
  prequalification STRING,
  high_sea_sh_risk STRING,
  procurement_document_type STRING,
  contract_type STRING,
  estimated_amount_usd DECIMAL(18, 2),
  actual_amount_usd DECIMAL(18, 2),
  process_status STRING,
  pdf_page INT NOT NULL,
  parser STRING NOT NULL,
  public_from DATE NOT NULL
)
