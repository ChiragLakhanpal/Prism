-- Data notes on plan rows: where a row's record is weak. This file is the one definition of each note.
--
-- method_differs_from_reference: STEP builds an Activity Reference No. from the method chosen when
-- the activity was created, so it can end in one method's code (KE-NWWDA-199461-GO-RFB) while the
-- Method column names another (Request for Quotations). Strata reads the method from the Method
-- column and notes the difference. The codes below are those whose STEP method name the fixture's
-- plans show; a reference that ends in any other code never makes this note. Each method name is
-- STEP's word for word, as src/strata/reader/step.py lists them in VALUES, and a test checks it.
-- RFP joined on October 30, 2026 (ticket 141): P161305's plan of September 24, 2026 writes
-- KE-KENHA-537932-CW-RFP with Request for Proposals, and P155350's plan of June 10, 2024 writes
-- its -RFP works, such as PK-SID-2961-CW-RFP, with Request for Bids, which this note now keeps.
--
-- actual_amount_zero: a row whose Process Status is Signed or Completed but whose Actual Amount
-- (US$) reads 0.00, so the record does not say what the contract cost.
--
-- method_unknown: a row whose Method cell is a name the method-name registry does not list
-- (config/method_names.toml; ticket 42), so method keeps the plan's words and Strata cannot match it to a
-- method in the Procurement Regulations.
INSERT INTO strata.silver.plan_data_notes (
  document_id, project_id, activity_reference_no, note, reference_method_code, reference_method,
  method, process_status, actual_amount_usd, public_from
)
SELECT
  r.document_id, r.project_id, r.activity_reference_no, 'method_differs_from_reference',
  c.code, c.method, r.method, r.process_status, r.actual_amount_usd, r.public_from
FROM strata.silver.plan_rows AS r
JOIN (
  VALUES
    ('RFB', 'Request for Bids'),
    ('RFQ', 'Request for Quotations'),
    ('RFP', 'Request for Proposals'),
    ('DIR', 'Direct Selection'),
    ('QCBS', 'Quality And Cost-Based Selection'),
    ('INDV', 'Individual Consultant Selection')
) AS c(code, method)
  ON c.code = regexp_extract(r.activity_reference_no, '-([A-Z]+)$', 1)
WHERE r.project_id = :project_id
  AND r.method IS NOT NULL
  AND r.method <> c.method
UNION ALL
SELECT
  r.document_id, r.project_id, r.activity_reference_no, 'actual_amount_zero',
  NULL, NULL, r.method, r.process_status, r.actual_amount_usd, r.public_from
FROM strata.silver.plan_rows AS r
WHERE r.project_id = :project_id
  AND r.process_status IN ('Signed', 'Completed')
  AND r.actual_amount_usd = 0
UNION ALL
SELECT
  r.document_id, r.project_id, r.activity_reference_no, 'method_unknown',
  NULL, NULL, r.method, r.process_status, r.actual_amount_usd, r.public_from
FROM strata.silver.plan_rows AS r
WHERE r.project_id = :project_id
  AND r.method IS NOT NULL
  AND r.method_original IS NOT NULL
  AND r.method_mapped IS NULL
