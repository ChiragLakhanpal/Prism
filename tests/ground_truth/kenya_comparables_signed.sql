-- The comparable works packages for KE-NWWDA-541055-CW-RFB, from gold.package with the default
-- criteria: Kenya, works, Request for Bids, first Invitation for Bids from July 1, 2019 to the
-- demo plan's date, October 9, 2026. They come from three projects (P156634, P176758 and
-- P170941), so the query names none.
--
-- The expected counts are tests/ground_truth/values.toml's [comparables]: 45 signed (signed = 45),
-- two of them only in their Contract Award notice (signed_only_in_award_notice = 2), and seven
-- not signed: three canceled (canceled = 3) and four still open (still_open = 4). A package's
-- canceled state comes from its plan row's Process Status, which ticket 08 reads from the
-- Procurement Plans, so this file counts the seven together.
-- param: first_notice_from = 2019-07-01
-- param: first_notice_to = 2026-10-09
-- expect: signed_in,packages
-- expect: award notice,2
-- expect: contract awards,43
-- expect: not signed,7
SELECT
  coalesce(signed_in, 'not signed') AS signed_in,
  count(*) AS packages
FROM strata.gold.package
WHERE country_code = 'KE'
  AND procurement_category = 'Works'
  AND procurement_method = 'Request for Bids'
  AND first_notice_date BETWEEN CAST(:first_notice_from AS DATE) AND CAST(:first_notice_to AS DATE)
GROUP BY coalesce(signed_in, 'not signed')
ORDER BY signed_in
