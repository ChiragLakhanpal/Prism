-- The estimates loop's watch (ticket 44): each package advertised by :as_of, with the inputs whose mix the watch
-- compares (estimates_loop.drift_inputs): those advertised before the champion's training date are the mix it
-- learned from, and those advertised in the watched month the mix it now meets.
SELECT k.step_reference, k.first_notice_date, k.procurement_category, k.procurement_method, k.review_type,
  k.public_from
FROM strata.gold.package AS k
WHERE k.first_notice_date IS NOT NULL
  AND k.first_notice_date <= :as_of
ORDER BY k.step_reference
