-- The comparable works packages for KE-NWWDA-541055-CW-RFB, from gold.package with the default
-- criteria: Kenya, works, Request for Bids, first Invitation for Bids from July 1, 2019 to the
-- demo plan's date, October 9, 2026. They come from three projects (P156634, P176758 and
-- P170941), so the query names none.
--
-- The expected counts are tests/ground_truth/values.toml's [comparables]: 45 signed (signed = 45),
-- two of them only in their Contract Award notice (signed_only_in_award_notice = 2), three
-- canceled (canceled = 3) and four still open (still_open = 4). A package that was not signed is
-- canceled when the newest Procurement Plan that lists it gives its Process Status as Canceled.
-- param: first_notice_from = 2019-07-01
-- param: first_notice_to = 2026-10-09
-- expect: state,packages
-- expect: award notice,2
-- expect: canceled,3
-- expect: contract awards,43
-- expect: still open,4
SELECT
  CASE
    WHEN signed_in IS NOT NULL THEN signed_in
    WHEN process_status = 'Canceled' THEN 'canceled'
    ELSE 'still open'
  END AS state,
  count(*) AS packages
FROM strata.gold.package
WHERE country_code = 'KE'
  AND procurement_category = 'Works'
  AND procurement_method = 'Request for Bids'
  AND first_notice_date BETWEEN CAST(:first_notice_from AS DATE) AND CAST(:first_notice_to AS DATE)
GROUP BY 1
ORDER BY 1
