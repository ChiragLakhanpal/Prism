-- The estimates loop's watch (ticket 44): every exposure public by :as_of with the dates Prism offered, from the
-- exposure log, the one place an exposure is defined (strata.ops.exposures).
SELECT e.exposure_id, e.step_reference, e.exposed_on, e.offered_middle_on, e.offered_eight_in_ten_on, e.public_from
FROM strata.ops.exposures AS e
WHERE e.public_from <= :as_of
ORDER BY e.step_reference, e.exposed_on, e.exposure_id
