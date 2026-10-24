-- Which of KE-NWWDA-541055-CW-RFB's comparables meet two criteria a call can add, as of October 22,
-- 2026, counted directly from the notices, the contracts and the plan rows, apart from
-- strata.gold.package and from find_comparables' own SQL. tests/test_find_comparables.py checks that
-- find_comparables returns these packages as its rows when the call sets each criterion.
--
-- Kenya works packages under Request for Bids whose first specific procurement notice is dated in
-- the period, July 1, 2019 to the plan's date, October 9, 2026:
--   Open - National     the newest public plan row that lists the package gives this Market
--                       Approach, and the package is not unsigned and marked Canceled there
--   1M to 2M US$        the package's contracts in the awards datasets add up to US$1,000,000 to
--                       US$2,000,000
-- param: as_of = 2026-10-22
-- param: notice_from = 2019-07-01
-- param: notice_to = 2026-10-09
-- engines: duckdb, databricks
-- expect: criterion,step_reference
-- expect: 1M to 2M US$,KE-GAWASCO-54759-CW-RFB
-- expect: 1M to 2M US$,KE-GAWASCO-54761-CW-RFB
-- expect: 1M to 2M US$,KE-GAWASCO-54763-CW-RFB
-- expect: 1M to 2M US$,KE-KIMAWASCO-158691-CW-RFB
-- expect: 1M to 2M US$,KE-MAWASCO-149056-CW-RFB
-- expect: 1M to 2M US$,KE-MOWASCO-228804-CW-RFB
-- expect: 1M to 2M US$,KE-NWWDA-229129-CW-RFB
-- expect: 1M to 2M US$,KE-WAJWASCO-372776-CW-RFB
-- expect: Open - National,KE-CWSB-232660-CW-RFB
-- expect: Open - National,KE-CWSB-233052-CW-RFB
-- expect: Open - National,KE-KIMAWASCO-141042-CW-RFB
-- expect: Open - National,KE-KIMAWASCO-142995-CW-RFB
-- expect: Open - National,KE-KIMAWASCO-158691-CW-RFB
-- expect: Open - National,KE-KIMAWASCO-416959-CW-RFB
-- expect: Open - National,KE-NWWDA-229129-CW-RFB
WITH noticed AS (
  SELECT step_reference, min(notice_date) AS noticed_on
  FROM strata.gold.notice
  WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
    AND step_reference IS NOT NULL AND notice_type NOT IN ('General Procurement Notice', 'Contract Award')
    AND public_from <= CAST(:as_of AS DATE)
  GROUP BY step_reference
),
in_period AS (
  SELECT step_reference FROM noticed
  WHERE noticed_on BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
),
amounts AS (
  SELECT step_reference, sum(contract_amount_usd) AS amount_usd
  FROM strata.gold.contract
  WHERE step_reference IS NOT NULL AND source LIKE 'awards%' AND public_from <= CAST(:as_of AS DATE)
  GROUP BY step_reference
),
newest_rows AS (
  SELECT r.activity_reference_no AS step_reference, r.market_approach, r.process_status
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= CAST(:as_of AS DATE)
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no ORDER BY v.plan_date DESC, r.pdf_page) = 1
)
SELECT 'Open - National' AS criterion, p.step_reference
FROM in_period AS p
JOIN newest_rows AS r ON r.step_reference = p.step_reference
LEFT JOIN amounts AS a ON a.step_reference = p.step_reference
WHERE r.market_approach = 'Open - National' AND NOT (a.amount_usd IS NULL AND r.process_status = 'Canceled')
UNION ALL
SELECT '1M to 2M US$', p.step_reference
FROM in_period AS p
JOIN amounts AS a ON a.step_reference = p.step_reference
WHERE a.amount_usd BETWEEN 1000000 AND 2000000
ORDER BY criterion, step_reference
