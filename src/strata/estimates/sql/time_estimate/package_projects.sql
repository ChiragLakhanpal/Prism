-- The time estimate's backtest (ticket 44): each package's project, so its unseen packages can be counted under the
-- edition of the procurement rules their project followed.
SELECT k.step_reference, k.project_id, k.public_from
FROM strata.gold.package AS k
WHERE k.public_from <= :as_of
