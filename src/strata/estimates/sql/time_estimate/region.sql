-- A country's World Bank region, as public on :as_of: a feature of a package described by its criteria rather
-- than a plan row (ticket 26, strata.estimates.time_estimate.described_features).
SELECT region, public_from
FROM strata.gold.country
WHERE country_code = :country_code AND public_from <= :as_of
