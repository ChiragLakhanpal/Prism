-- One STEP row per activity in each plan version the layout parser read, in STEP's columns and
-- with STEP's values word for word. The method comes from the Method column, never from the
-- reference. A column the plan's template lacks is empty.
--
-- document_id                 the plan version
-- project_id                  its project
-- section                     the table the row sits in: WORKS, GOODS, NON CONSULTING SERVICES,
--                             CONSULTING FIRMS or INDIVIDUAL CONSULTANTS
-- activity_reference_no       Activity Reference No., repaired where one look-alike swap makes a broken one whole
--                             and a notice or plan version carries it (src/strata/reader/repair.py; ticket 131)
-- description                 Description, with each word the PDF cell split at a wrap joined where the project's
--                             notices or the version's other rows write it whole (ticket 131)
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
-- method_original             the Method cell as the plan writes it, such as STEP's French "Appel d'offres"
--                             (ticket 42); empty when the cell is
-- method_original_lang        the language of those words (config/method_names.toml), or empty for a name the
--                             registry does not list
-- method_mapped               true when the plan's words are an old or a French name stored as the current name
--                             in method; false when they are the current name; empty for a name the registry
--                             does not list, which method keeps as written and plan_data_notes notes
-- activity_reference_no_as_read the reference as the layout parser read it, which the source view shows
-- reference_repair            why activity_reference_no differs from it, or why it is flagged: look_alike (one
--                             look-alike swap, carried by a record), plan_text (the plan's text gives it, ticket 78)
--                             or reference_as_read (it breaks STEP's grammar and stays as the plan gives it); empty
--                             for a reference kept as read
-- reference_carried_by        the evidence id of the record that carries the reference kept: a notice
--                             (strata.silver.notices:{notice_id}), another version's row or a version's text
-- description_as_read         the Description as the layout parser read it, a space at each wrap, which the source
--                             view shows
-- description_joins           each split word joined, as JSON: [{"read", "joined", "found_in"}], found_in notices
--                             or plan; empty when none was
-- pdf_page                    the PDF page the row is on
-- parser                      the layout parser that read the page
-- public_from                 the version's public date (ADR 0002)
--
-- A table made before ticket 131 lacks activity_reference_no_as_read, reference_repair, reference_carried_by,
-- description_as_read and description_joins, and CREATE TABLE IF NOT EXISTS adds none. On such a workspace,
-- run this once before any bundle or App deploy; it puts the columns last:
--   ALTER TABLE strata.silver.plan_rows ADD COLUMNS (activity_reference_no_as_read STRING, reference_repair STRING,
--     reference_carried_by STRING, description_as_read STRING, description_joins STRING)
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
  method_original STRING,
  method_original_lang STRING,
  method_mapped BOOLEAN,
  activity_reference_no_as_read STRING,
  reference_repair STRING,
  reference_carried_by STRING,
  description_as_read STRING,
  description_joins STRING,
  pdf_page INT NOT NULL,
  parser STRING NOT NULL,
  public_from DATE NOT NULL
)
