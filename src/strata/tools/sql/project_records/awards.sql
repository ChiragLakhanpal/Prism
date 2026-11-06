-- project_records: the project's contracts signed after a date (the latest ISR's), public by the as-of date,
-- oldest first, with the supplier as the award record names it. An individual consultant has no name
-- (gold.supplier), and Prism never names a person.
SELECT
  c.contract_id,
  c.source,
  c.step_reference,
  c.contract_description,
  c.procurement_category,
  c.contract_signing_date,
  c.contract_amount_usd,
  c.contract_amount,
  c.contract_currency,
  s.name AS supplier_name,
  s.kind AS supplier_kind,
  c.public_from
FROM strata.gold.contract AS c
LEFT JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id
WHERE c.project_id = :project_id
  AND c.public_from <= :as_of
  AND c.contract_signing_date > :since
ORDER BY c.contract_signing_date, c.contract_id
