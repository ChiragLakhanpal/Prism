-- estimate_time: what each package matching the comparables' method, category and country criteria went with,
-- as its records public on the as-of date give it (ticket 26). estimate_time keeps the packages find_comparables
-- returned and counts the rest out.
--
-- market_approach   Market Approach in the newest plan version that lists it, else what its contracts or its
--                   specific procurement notice say (only an old method name such as ICB gives one there),
--                   as find_comparables reads it
-- prequalification  Prequalification (Y/N) in that newest plan version, Y or N; empty when none is recorded
-- lots              how many contracts the awards dataset holds for it: the glossary's lot is awarded as its own
--                   contract. Empty for a package with no contract yet, whose lots are not recorded.
-- amount_usd        its signed contracts in US dollars, added up, for the size reason; empty with no contract
WITH listed AS (
  SELECT r.activity_reference_no AS step_reference, r.market_approach, r.prequalification
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
),
signed AS (
  SELECT step_reference, count(*) AS lots, sum(contract_amount_usd) AS amount_usd, min(market_approach) AS market_approach
  FROM strata.gold.contract
  WHERE step_reference IS NOT NULL AND source <> 'notices' AND public_from <= :as_of
  GROUP BY step_reference
)
SELECT
  p.step_reference,
  coalesce(l.market_approach, s.market_approach, n.market_approach) AS market_approach,
  CASE WHEN upper(l.prequalification) IN ('Y', 'N') THEN upper(l.prequalification) END AS prequalification,
  s.lots,
  s.amount_usd
FROM strata.gold.package AS p
LEFT JOIN strata.gold.notice AS n ON n.notice_id = p.first_notice_id AND n.public_from <= :as_of
LEFT JOIN listed AS l ON l.step_reference = p.step_reference
LEFT JOIN signed AS s ON s.step_reference = p.step_reference
WHERE p.public_from <= :as_of
  AND (CAST(:country AS STRING) IS NULL OR upper(p.country_code) = upper(:country))
  AND (CAST(:method AS STRING) IS NULL OR lower(p.procurement_method) = lower(:method))
  AND (CAST(:category AS STRING) IS NULL OR lower(p.procurement_category) = lower(:category))
ORDER BY p.step_reference
