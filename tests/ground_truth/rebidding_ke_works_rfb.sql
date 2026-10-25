-- How many of KE-NWWDA-541055-CW-RFB's comparable packages were advertised again, with the default criteria, as
-- of October 22, 2026, counted directly from the notices, the contracts and the plan rows, apart from
-- strata.gold.package and from rebidding_risk's own SQL. tests/ground_truth/values.toml's [rebidding] entry gives
-- the same counts from the recorded files, and evals/benchmark.yaml's rebidding question checks the tool states
-- them.
--
-- Kenya works packages under Request for Bids whose first specific procurement notice is dated July 1, 2019 to
-- the plan's date, October 9, 2026, the canceled ones included:
--   comparables         all of them
--   no award            unsigned (no contract in the awards dataset and no Contract Award notice with a signature
--                       date, each public by the as-of date) 548 days or more after their bids were due
--                       (config/thresholds.toml, rebidding.no_award_after_days)
--   same reference      a second Invitation for Bids under the same STEP reference
--   canceled plan row   unsigned and Canceled in the newest plan public on the as-of date that lists them
--   advertised again    any of the three, each package once
-- param: as_of = 2026-10-22
-- param: notice_from = 2019-07-01
-- param: notice_to = 2026-10-09
-- param: wait_days = 548
-- engines: duckdb, databricks
-- expect: measure,packages
-- expect: advertised again,3
-- expect: canceled plan row,3
-- expect: comparables,52
-- expect: no award,3
-- expect: same reference,0
WITH invitations AS (
  SELECT step_reference, notice_date, submission_deadline
  FROM strata.gold.notice
  WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
    AND step_reference IS NOT NULL AND notice_type NOT IN ('General Procurement Notice', 'Contract Award')
    AND public_from <= CAST(:as_of AS DATE)
),
noticed AS (
  SELECT step_reference, min(notice_date) AS noticed_on, min_by(submission_deadline, notice_date) AS bids_due,
    count(*) AS invitations
  FROM invitations
  GROUP BY step_reference
),
signings AS (
  SELECT step_reference FROM strata.gold.contract
  WHERE step_reference IS NOT NULL AND source = 'awards' AND public_from <= CAST(:as_of AS DATE)
  UNION ALL
  SELECT step_reference FROM strata.gold.notice
  WHERE step_reference IS NOT NULL AND notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL
    AND public_from <= CAST(:as_of AS DATE)
),
statuses AS (
  SELECT r.activity_reference_no AS step_reference, r.process_status
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= CAST(:as_of AS DATE)
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no ORDER BY v.plan_date DESC, r.pdf_page) = 1
),
comparables AS (
  SELECT
    n.step_reference,
    n.step_reference IN (SELECT step_reference FROM signings) AS signed,
    date_add(coalesce(n.bids_due, n.noticed_on), CAST(:wait_days AS INT)) <= CAST(:as_of AS DATE) AS waited,
    n.invitations > 1 AS twice,
    coalesce(t.process_status, '') = 'Canceled' AS canceled
  FROM noticed AS n
  LEFT JOIN statuses AS t ON t.step_reference = n.step_reference
  WHERE n.noticed_on BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
)
SELECT 'comparables' AS measure, count(*) AS packages FROM comparables
UNION ALL
SELECT 'no award', count(*) FROM comparables WHERE NOT signed AND waited
UNION ALL
SELECT 'same reference', count(*) FROM comparables WHERE twice
UNION ALL
SELECT 'canceled plan row', count(*) FROM comparables WHERE NOT signed AND canceled
UNION ALL
SELECT 'advertised again', count(*) FROM comparables WHERE (NOT signed AND (waited OR canceled)) OR twice
ORDER BY measure
