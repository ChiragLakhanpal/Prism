-- Every supplier on the project's contracts public by the as-of date (ADR 0002), for the sanctions reader (ticket 154):
-- each member of a joint venture from strata.gold.contract_supplier, and each contract's own supplier unless it is the
-- joint venture itself. A supplier with no name (an individual consultant, whose name the record leaves out) is listed
-- too, so the reader can say how many it could not check.
SELECT DISTINCT s.supplier_id, s.name
FROM strata.gold.contract AS c
JOIN strata.gold.contract_supplier AS cs ON cs.contract_id = c.contract_id
JOIN strata.gold.supplier AS s ON s.supplier_id = cs.supplier_id
WHERE c.project_id = :project_id
  AND c.public_from <= :as_of
UNION
SELECT DISTINCT s.supplier_id, s.name
FROM strata.gold.contract AS c
JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id
WHERE c.project_id = :project_id
  AND c.public_from <= :as_of
  AND s.kind <> 'joint venture'
ORDER BY supplier_id
