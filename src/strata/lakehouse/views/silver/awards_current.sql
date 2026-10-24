-- Each contract's award rows as the newest fetch of each page gives them, one row per supplier.
-- What is current is decided by page, not by day: for each request, the page bronze kept last
-- (strata.bronze.current_pages). An unchanged page keeps its first fetch day and still counts, so
-- a joint venture whose members sit on two pages keeps both when a later fetch changes one page
-- only. A supplier row that a later fetch of the same request no longer holds is left out, so gold
-- never adds a share that the source took back. Where two current pages hold the same supplier
-- row, the newest one is kept.
-- gold.contract, gold.contract_supplier, gold.supplier and the awards' data readiness measures
-- read this view, so the rule is written once.
CREATE OR REPLACE VIEW strata.silver.awards_current AS
SELECT a.*
FROM strata.silver.awards AS a
JOIN strata.bronze.current_pages AS p ON p.page_hash = a.page_hash
QUALIFY row_number() OVER (PARTITION BY a.wb_contract_number, a.supplier_id ORDER BY a.fetched_at DESC, a.page_hash) = 1
