-- find_comparables: the latest day the notices and contract awards it read run through, on or before
-- the as-of date, for the source line ("Records run through ...").
SELECT greatest(
  (SELECT max(notice_date) FROM strata.gold.notice WHERE public_from <= :as_of),
  (SELECT max(contract_signing_date) FROM strata.gold.contract WHERE source = 'awards' AND public_from <= :as_of)
) AS records_through
