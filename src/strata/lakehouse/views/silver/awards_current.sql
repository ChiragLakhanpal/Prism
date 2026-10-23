-- Each contract's award rows as the newest fetch of it gives them, one row per supplier: the rows
-- from the newest day a fetched page held the contract. A supplier row that a later fetch of the
-- contract no longer holds is left out, so gold never adds a share that the source took back.
-- gold.contract, gold.contract_supplier, gold.supplier and the awards' data readiness measures
-- read this view, so the rule is written once.
CREATE OR REPLACE VIEW strata.silver.awards_current AS
SELECT *
FROM strata.silver.awards
QUALIFY CAST(fetched_at AS DATE) = max(CAST(fetched_at AS DATE)) OVER (PARTITION BY wb_contract_number)
  AND row_number() OVER (PARTITION BY wb_contract_number, supplier_id ORDER BY fetched_at DESC, page_hash) = 1
