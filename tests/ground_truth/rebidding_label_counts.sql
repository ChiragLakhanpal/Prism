-- How many packages each rebidding label source names on the fixture, as of October 23, 2026, the day the
-- fixture's nightly run counted them, counted directly from the notices, the contracts and the plan rows, apart
-- from strata.gold.package and from the labels' own SQL (src/strata/estimates/sql/rebidding/labels.sql).
-- tests/test_rebidding_risk.py checks that strata.ops.rebidding_labels holds the same counts.
--
-- Every STEP reference whose first specific procurement notice (not a General Procurement Notice or a Contract
-- Award) is dated from July 1, 2019 (past_range.period_from) and was public on the as-of date, in every
-- category and country the fixture holds:
--   no_award        unsigned (no contract in the awards dataset and no Contract Award notice with a signature
--                   date, each public by the as-of date) 548 days or more after its bids were due
--                   (rebidding.no_award_after_days): the three canceled works packages, and nine goods and
--                   consultants' packages of P156634 whose notices no award followed
--   same_reference  a second notice of the same type under the same STEP reference: none
--   canceled_row    unsigned and Canceled in the newest plan public on the as-of date that lists it: the three
--                   Kilifi works packages
--   any             one or more of the three, each package once
-- param: as_of = 2026-10-23
-- param: period_from = 2019-07-01
-- param: wait_days = 548
-- engines: duckdb, databricks
-- expect: source,count,denominator
-- expect: any,12,139
-- expect: canceled_row,3,139
-- expect: no_award,12,139
-- expect: same_reference,0,139
WITH specific AS (
  SELECT step_reference, notice_type, notice_date, submission_deadline
  FROM strata.gold.notice
  WHERE step_reference IS NOT NULL AND notice_type NOT IN ('General Procurement Notice', 'Contract Award')
    AND public_from <= CAST(:as_of AS DATE)
),
firsts AS (
  SELECT step_reference, min(notice_date) AS noticed_on, min_by(submission_deadline, notice_date) AS bids_due,
    min_by(notice_type, notice_date) AS first_type
  FROM specific
  GROUP BY step_reference
),
repeated AS (
  SELECT f.step_reference
  FROM firsts AS f
  JOIN specific AS s ON s.step_reference = f.step_reference AND s.notice_type = f.first_type
   AND s.notice_date > f.noticed_on
  GROUP BY f.step_reference
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
packages AS (
  SELECT
    f.step_reference,
    f.step_reference IN (SELECT step_reference FROM signings) AS signed,
    date_add(coalesce(f.bids_due, f.noticed_on), CAST(:wait_days AS INT)) <= CAST(:as_of AS DATE) AS waited,
    f.step_reference IN (SELECT step_reference FROM repeated) AS again,
    coalesce(t.process_status, '') = 'Canceled' AS canceled
  FROM firsts AS f
  LEFT JOIN statuses AS t ON t.step_reference = f.step_reference
  WHERE f.noticed_on >= CAST(:period_from AS DATE)
),
counted AS (
  SELECT 'no_award' AS source, count_if(NOT signed AND waited) AS count, count(*) AS denominator FROM packages
  UNION ALL
  SELECT 'same_reference', count_if(again), count(*) FROM packages
  UNION ALL
  SELECT 'canceled_row', count_if(NOT signed AND canceled), count(*) FROM packages
  UNION ALL
  SELECT 'any', count_if((NOT signed AND (waited OR canceled)) OR again), count(*) FROM packages
)
SELECT source, count, denominator FROM counted ORDER BY source
