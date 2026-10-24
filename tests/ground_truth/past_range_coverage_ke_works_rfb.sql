-- The coverage line of KE-NWWDA-541055-CW-RFB's past range with the default criteria, as of
-- October 22, 2026, counted directly from the notices, the contracts and the plan rows, apart from
-- strata.gold.package and from find_comparables' own SQL. tests/test_find_comparables.py checks that
-- the tool's coverage line states these counts.
--
-- Kenya works packages under Request for Bids:
--   used                 each STEP reference whose first specific procurement notice is dated in the
--                        period, July 1, 2019 to the plan's date, October 9, 2026 (52), less the three
--                        canceled: values.toml's 45 signed and four still open
--   canceled             of those, unsigned and marked Canceled in the newest plan that lists them
--   no notice            a STEP reference signed in the period with no specific procurement notice
--                        Strata holds: the ten county and ICT packages of P176758 and P170941, whose
--                        award rows the fixture records but whose notices it does not
--   no STEP reference    a contract in the awards dataset signed in the period whose reference is not
--                        a STEP reference (LOT I, and two references with extra parts)
--   matched              all four together
-- param: as_of = 2026-10-22
-- param: notice_from = 2019-07-01
-- param: notice_to = 2026-10-09
-- expect: measure,packages
-- expect: canceled,3
-- expect: matched,65
-- expect: no STEP reference,3
-- expect: no notice,10
-- expect: used,49
WITH noticed AS (
  SELECT step_reference, min(notice_date) AS noticed_on
  FROM strata.gold.notice
  WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
    AND step_reference IS NOT NULL AND notice_type NOT IN ('General Procurement Notice', 'Contract Award')
    AND public_from <= CAST(:as_of AS DATE)
  GROUP BY step_reference
),
signings AS (
  SELECT step_reference, contract_signing_date AS signed_on
  FROM strata.gold.contract
  WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
    AND step_reference IS NOT NULL AND source = 'awards' AND public_from <= CAST(:as_of AS DATE)
  UNION ALL
  SELECT step_reference, contract_signature_date AS signed_on
  FROM strata.gold.notice
  WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
    AND step_reference IS NOT NULL AND notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL
    AND public_from <= CAST(:as_of AS DATE)
),
signed AS (
  SELECT step_reference, min(signed_on) AS signed_on FROM signings GROUP BY step_reference
),
statuses AS (
  SELECT r.activity_reference_no AS step_reference, r.process_status
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= CAST(:as_of AS DATE)
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no ORDER BY v.plan_date DESC, r.pdf_page) = 1
),
in_period AS (
  SELECT n.step_reference, s.signed_on, t.process_status
  FROM noticed AS n
  LEFT JOIN signed AS s ON s.step_reference = n.step_reference
  LEFT JOIN statuses AS t ON t.step_reference = n.step_reference
  WHERE n.noticed_on BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
),
counted AS (
  SELECT 'used' AS measure, count(*) AS packages
  FROM in_period WHERE signed_on IS NOT NULL OR coalesce(process_status, '') <> 'Canceled'
  UNION ALL
  SELECT 'canceled', count(*)
  FROM in_period WHERE signed_on IS NULL AND process_status = 'Canceled'
  UNION ALL
  SELECT 'no notice', count(*)
  FROM signed AS s
  WHERE s.signed_on BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
    AND s.step_reference NOT IN (SELECT step_reference FROM noticed)
  UNION ALL
  SELECT 'no STEP reference', count(*)
  FROM strata.gold.contract
  WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
    AND step_reference IS NULL AND source = 'awards' AND public_from <= CAST(:as_of AS DATE)
    AND contract_signing_date BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
)
SELECT measure, packages FROM counted
UNION ALL
SELECT 'matched', sum(packages) FROM counted
ORDER BY measure
