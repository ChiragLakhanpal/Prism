-- The exposure log (ticket 44): a package's first specific procurement notice, when it was published on or before
-- the as-of date. Procurement cycle time runs from it (GLOSSARY.md), as find_comparables measures it, so the dates
-- Prism offers count from it once the package is advertised.
SELECT p.step_reference, p.first_notice_date, p.first_notice_date AS public_from
FROM strata.gold.package AS p
WHERE p.step_reference = :step_reference
  AND p.first_notice_date IS NOT NULL
  AND p.first_notice_date <= :as_of
